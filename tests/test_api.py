import io

import docx
import pytest
from fastapi.testclient import TestClient

from jobsearch_api.main import create_app

from conftest import SAMPLE_RESUME


@pytest.fixture()
def client():
    return TestClient(create_app())


def test_healthz(client):
    body = client.get("/healthz").json()
    assert body["status"] == "ok"
    assert body["providersTotal"] >= 6
    assert body["providersConfigured"] >= 1  # sample is always configured


def test_providers_endpoint_lists_setup_hints(client):
    providers = client.get("/api/providers").json()
    names = {p["name"] for p in providers}
    assert {"linkedin", "indeed", "glassdoor", "handshake", "adzuna", "jooble", "sample"} <= names
    handshake = next(p for p in providers if p["name"] == "handshake")
    assert handshake["configured"] is False  # no cookie in test env
    assert "HANDSHAKE_COOKIE" in handshake["setupHint"]


def test_resume_upload_txt(client):
    resp = client.post(
        "/api/resume",
        files={"file": ("resume.txt", SAMPLE_RESUME.encode(), "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["resumeId"]
    assert "python" in body["profile"]["skills"]
    assert body["profile"]["seniority"]


def test_resume_upload_docx(client):
    buffer = io.BytesIO()
    document = docx.Document()
    document.add_paragraph("Senior Software Engineer. 7+ years Python, Go, Kubernetes.")
    document.save(buffer)
    resp = client.post(
        "/api/resume", files={"file": ("resume.docx", buffer.getvalue(), "application/vnd...")}
    )
    assert resp.status_code == 200
    profile = resp.json()["profile"]
    assert "python" in profile["skills"]
    assert profile["seniority"] == "senior"


def test_resume_requires_content(client):
    resp = client.post("/api/resume")
    assert resp.status_code == 400


def test_resume_text_endpoint(client):
    resp = client.post("/api/resume/text", json={"text": SAMPLE_RESUME})
    assert resp.status_code == 200
    assert resp.json()["resumeId"]


def _search(client, **overrides):
    payload = {
        "keywords": "engineer",
        "providers": ["sample"],
        "resumeText": SAMPLE_RESUME,
    }
    payload.update(overrides)
    return client.post("/api/jobs/search", json=payload)


def test_search_scores_and_uses_camel_case(client):
    resp = _search(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["scored"] is True
    assert body["jobs"], "sample provider should return jobs"
    job = body["jobs"][0]
    assert {"id", "source", "sourceDisplay", "title", "score", "breakdown"} <= set(job)
    assert 0 <= job["score"] <= 100
    assert job["breakdown"]["matchedSkills"] is not None
    scores = [j["score"] for j in body["jobs"]]
    assert scores == sorted(scores, reverse=True)
    provider = body["providers"][0]
    assert provider["provider"] == "sample" and provider["status"] == "ok"
    assert provider["elapsedMs"] >= 0


def test_search_with_resume_id_flow(client):
    upload = client.post(
        "/api/resume", files={"file": ("r.txt", SAMPLE_RESUME.encode(), "text/plain")}
    ).json()
    resp = _search(client, resumeId=upload["resumeId"], resumeText=None)
    assert resp.status_code == 200
    assert resp.json()["scored"] is True


def test_search_unknown_resume_id_404(client):
    resp = _search(client, resumeId="does-not-exist", resumeText=None)
    assert resp.status_code == 404


def test_search_min_score_filter(client):
    resp = _search(client, minScore=100)
    assert resp.status_code == 200
    assert all(j["score"] >= 100 for j in resp.json()["jobs"])


def test_search_reports_unknown_provider(client):
    resp = _search(client, providers=["nope", "sample"])
    providers = {p["provider"]: p for p in resp.json()["providers"]}
    assert providers["nope"]["status"] == "error"


def test_placeholder_ui_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Placeholder UI" in resp.text
