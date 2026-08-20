from datetime import date

from jobsearch_engine import Job
from jobsearch_engine.dedupe import dedupe_jobs


def _job(**overrides) -> Job:
    defaults = dict(
        id="x:1",
        source="linkedin",
        title="Data Engineer",
        company="Acme Analytics",
        location="New York, NY",
        url="https://linkedin.com/jobs/1",
        posted_at=date(2026, 8, 1),
    )
    defaults.update(overrides)
    return Job(**defaults)


def test_merges_same_role_across_providers():
    jobs = [
        _job(source="linkedin", url="https://linkedin.com/jobs/1", description=None),
        _job(
            id="x:2",
            source="indeed",
            url="https://indeed.com/jobs/1",
            description="Build pipelines with Spark and Airflow",
        ),
    ]
    unique, removed = dedupe_jobs(jobs)
    assert removed == 1
    assert len(unique) == 1
    # Keeps the richer (indeed) description.
    assert unique[0].description and "Spark" in unique[0].description
    assert unique[0].extra["also_found_on"] == ["linkedin"]


def test_company_suffixes_normalized():
    jobs = [
        _job(company="Acme Analytics", url=None),
        _job(id="x:2", source="glassdoor", company="Acme Analytics Inc.", url=None),
    ]
    unique, removed = dedupe_jobs(jobs)
    assert removed == 1
    assert len(unique) == 1


def test_same_url_different_titles_merges():
    jobs = [
        _job(title="Data Engineer"),
        _job(id="x:2", source="indeed", title="Senior Data Engineer"),
    ]
    unique, removed = dedupe_jobs(jobs)
    assert removed == 1


def test_different_roles_kept():
    jobs = [
        _job(title="Data Engineer"),
        _job(id="x:2", source="indeed", title="Data Scientist", url="https://indeed.com/2"),
    ]
    unique, removed = dedupe_jobs(jobs)
    assert removed == 0
    assert len(unique) == 2


def test_tracking_params_stripped():
    jobs = [
        _job(url="https://boards.com/jobs/123"),
        _job(
            id="x:2",
            source="indeed",
            url="https://www.boards.com/jobs/123/?utm_source=linkedin",
        ),
    ]
    unique, removed = dedupe_jobs(jobs)
    assert removed == 1
