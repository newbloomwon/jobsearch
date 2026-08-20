from datetime import date, timedelta

import pytest

from jobsearch_engine import Job, JobQuery, ResumeProfile, search
from jobsearch_engine.providers.base import JobProvider, ProviderError
from jobsearch_engine.providers.sample import SampleProvider


class BrokenProvider(JobProvider):
    name = "broken"
    display_name = "Broken Co"

    async def search(self, query):
        raise ProviderError("upstream exploded")


class SlowProvider(JobProvider):
    name = "slow"
    display_name = "Slow Co"

    async def search(self, query):
        import asyncio

        await asyncio.sleep(10)
        return []


class DelayedSampleProvider(SampleProvider):
    """Sample data pretending to be another provider (different source tag)."""

    name = "sample2"
    display_name = "Sample Too"


@pytest.fixture
def registry():
    return {
        "sample": SampleProvider(),
        "broken": BrokenProvider(),
        "slow": SlowProvider(),
    }


async def test_search_returns_jobs_and_provider_metadata(registry):
    result = await search(JobQuery(keywords="engineer"), registry)
    assert result.jobs, "sample provider should return jobs"
    statuses = {p.provider: p.status for p in result.providers}
    assert statuses["sample"] == "ok"
    assert statuses["broken"] == "error"
    # The broken provider's error message is surfaced for the UI.
    broken = next(p for p in result.providers if p.provider == "broken")
    assert "exploded" in (broken.error or "")


async def test_one_provider_timeout_doesnt_kill_search(registry):
    result = await search(JobQuery(keywords="engineer"), registry, timeout_s=0.2)
    statuses = {p.provider: p.status for p in result.providers}
    assert statuses["slow"] == "timeout"
    assert statuses["sample"] == "ok"
    assert result.jobs


async def test_sample_excluded_from_defaults_when_real_providers_exist():
    class RealProvider(JobProvider):
        name = "real"
        display_name = "Real Board"

        async def search(self, query):
            return [Job(id="r:1", source="real", title="Software Engineer")]

    registry = {"real": RealProvider(), "sample": SampleProvider()}
    result = await search(JobQuery(keywords="engineer"), registry)
    assert {p.provider for p in result.providers} == {"real"}
    assert all(j.source != "sample" for j in result.jobs)


async def test_sample_is_fallback_when_nothing_configured():
    class LockedProvider(JobProvider):
        name = "locked"
        display_name = "Locked Board"

        def is_configured(self) -> bool:
            return False

        async def search(self, query):  # pragma: no cover
            return []

    registry = {"locked": LockedProvider(), "sample": SampleProvider()}
    result = await search(JobQuery(keywords="engineer"), registry)
    assert {p.provider for p in result.providers} == {"sample"}
    assert result.jobs


async def test_unknown_provider_reported(registry):
    result = await search(JobQuery(keywords="engineer"), registry, requested=["nope"])
    assert result.providers[0].status == "error"
    assert "Unknown provider" in result.providers[0].error


async def test_dedupe_across_providers_counts_removed():
    registry = {"sample": SampleProvider(), "sample2": DelayedSampleProvider()}
    result = await search(JobQuery(keywords="data engineer"), registry)
    # The Acme Analytics Data Engineer posting appears in both feeds.
    assert result.duplicates_removed >= 1
    merged = [j for j in result.jobs if j.company and "Acme" in j.company]
    assert len(merged) == 1
    assert "sample2" in merged[0].extra.get("also_found_on", [])


async def test_scoring_orders_jobs_for_profile():
    from datetime import date

    from jobsearch_engine import ResumeProfile

    strong_desc = (
        "Requirements: 4+ years with Python and React. TypeScript and PostgreSQL "
        "required. Docker in production."
    )
    weak_desc = "Requirements: 8+ years of Java and Spring. Android and Kotlin required."
    profile = ResumeProfile(
        skills=["python", "react", "typescript", "postgresql", "docker"],
        titles=["Software Engineer"],
        seniority="mid",
        years_experience=5,
        tokens={"python": 3, "react": 2},
    )

    class FakeProvider(JobProvider):
        name = "fake"
        display_name = "Fake"

        async def search(self, query):
            return [
                Job(id="f:1", source="fake", title="Software Engineer", description=strong_desc),
                Job(id="f:2", source="fake", title="Software Engineer", description=weak_desc),
            ]

    result = await search(
        JobQuery(keywords="engineer"), {"fake": FakeProvider()}, profile=profile
    )
    assert result.scored is True
    scores = [j.score for j in result.jobs]
    assert scores == sorted(scores, reverse=True)
    assert result.jobs[0].description == strong_desc
    assert result.jobs[0].breakdown is not None


async def test_unscored_search_orders_by_date():
    result = await search(JobQuery(keywords="engineer"), {"sample": SampleProvider()})
    assert result.scored is False
    dates = [j.posted_at for j in result.jobs if j.posted_at]
    assert dates == sorted(dates, reverse=True)


async def test_limit_applied():
    result = await search(
        JobQuery(keywords="engineer"), {"sample": SampleProvider()}, limit=3
    )
    assert len(result.jobs) <= 3


async def test_hours_old_filters_sample():
    result = await search(
        JobQuery(keywords="engineer", hours_old=48), {"sample": SampleProvider()}
    )
    oldest_allowed = date(2026, 8, 19) - timedelta(days=3)
    assert all(j.posted_at >= oldest_allowed for j in result.jobs)
