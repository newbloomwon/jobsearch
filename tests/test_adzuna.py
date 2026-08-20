import pytest
import httpx

from jobsearch_engine import JobQuery
from jobsearch_engine.providers.adzuna import AdzunaProvider

_PAYLOAD = {
    "results": [
        {
            "id": "991",
            "title": "Python Developer",
            "description": "Django and PostgreSQL shop.",
            "redirect_url": "https://adzuna.com/detail/991",
            "created": "2026-08-18T10:00:00Z",
            "company": {"displayname": "Cloudline"},
            "location": {"displayname": "New York, NY"},
            "salary_min": 120000.0,
            "salary_max": 140000.0,
            "currency": "USD",
            "contract_type": "full_time",
        }
    ]
}


def _client(payload=_PAYLOAD, status=200, requests_seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if requests_seen is not None:
            requests_seen.append(request)
        return httpx.Response(status, json=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_maps_adzuna_response():
    seen: list = []
    provider = AdzunaProvider(app_id="x", app_key="y", client=_client(requests_seen=seen))
    jobs = await provider.search(JobQuery(keywords="python developer", country="USA"))
    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "adzuna"
    assert job.company == "Cloudline"
    assert job.location == "New York, NY"
    assert str(job.posted_at) == "2026-08-18"
    assert job.salary_max == 140000.0
    assert job.job_type == "fulltime"
    # Credentials and search term reached the API, USA mapped to "us".
    url = str(seen[0].url)
    assert "app_id=x" in url and "app_key=y" in url
    assert "what=python+developer" in url and "/jobs/us/search/1" in url


async def test_bad_credentials_raises_provider_error():
    provider = AdzunaProvider(app_id="x", app_key="y", client=_client(status=401))
    with pytest.raises(Exception, match="credentials"):
        await provider.search(JobQuery(keywords="dev"))


def test_not_configured_without_keys():
    provider = AdzunaProvider()
    assert provider.is_configured() is False
    assert "ADZUNA_APP_ID" in provider.not_configured_reason()
