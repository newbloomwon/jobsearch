import httpx
import pytest

from jobsearch_engine import JobQuery
from jobsearch_engine.providers.jooble import JoobleProvider, parse_salary


def test_parse_salary_ranges():
    assert parse_salary("$120k - $150k a year") == (120000, 150000, "yearly")
    assert parse_salary("$45 - $60/hr") == (45, 60, "hourly")
    assert parse_salary("100000 a year") == (100000, 100000, "yearly")
    assert parse_salary("") == (None, None, None)


def _client(payload, status=200, requests_seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if requests_seen is not None:
            requests_seen.append(request)
        return httpx.Response(status, json=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_maps_jooble_response():
    seen: list = []
    payload = {
        "jobs": [
            {
                "id": "55",
                "title": "React Developer",
                "company": "Pixel",
                "location": "Remote",
                "snippet": "React and TypeScript work.",
                "salary": "$100k - $130k a year",
                "link": "https://jooble.org/apply/55",
                "updated": "2026-08-17 09:00:00.0",
                "source": "Company site",
            }
        ]
    }
    provider = JoobleProvider(api_key="key123", client=_client(payload, requests_seen=seen))
    jobs = await provider.search(JobQuery(keywords="react", location="remote"))
    job = jobs[0]
    assert job.title == "React Developer"
    assert job.salary_min == 100000 and job.salary_max == 130000
    assert str(job.posted_at) == "2026-08-17"
    assert job.description == "React and TypeScript work."
    assert seen[0].url.path == "/api/key123"


async def test_error_surfaces_on_401():
    provider = JoobleProvider(api_key="bad", client=_client({"": ""}, status=401))
    with pytest.raises(Exception, match="API key"):
        await provider.search(JobQuery(keywords="react"))


def test_not_configured_without_key():
    assert JoobleProvider().is_configured() is False
