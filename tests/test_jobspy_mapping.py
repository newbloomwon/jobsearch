"""JobSpy row → Job mapping, tested with plain dicts (no pandas/network)."""
from datetime import date

from jobsearch_engine.providers.jobspy_provider import JobSpyProvider, row_to_job


def test_maps_typical_row():
    row = {
        "title": "Backend Engineer",
        "company": "Initech",
        "company_url_direct": "https://initech.com",
        "location": "Austin, TX",
        "job_type": "FULLTIME",
        "is_remote": False,
        "date_posted": "2026-08-15",
        "job_url": "https://indeed.com/viewjob?jk=abc123",
        "min_amount": 120000.0,
        "max_amount": 150000.0,
        "interval": "yearly",
        "currency": "USD",
        "description": "Python, Go, Kubernetes",
        "job_level": "Mid-Senior",
    }
    job = row_to_job("indeed", row)
    assert job.source == "indeed"
    assert job.source_display == "Indeed"
    assert job.title == "Backend Engineer"
    assert job.company == "Initech"
    assert job.posted_at == date(2026, 8, 15)
    assert job.salary_min == 120000.0 and job.salary_max == 150000.0
    assert job.salary_period == "yearly"
    assert job.job_type == "fulltime"
    assert job.extra["job_level"] == "Mid-Senior"


def test_maps_nested_compensation_row():
    row = {
        "title": "Data Scientist",
        "company": " Umbrella ",
        "job_url": "https://linkedin.com/jobs/42",
        "compensation": {
            "min_amount": 100,
            "max_amount": 120,
            "interval": "hourly",
            "currency": "USD",
        },
    }
    job = row_to_job("linkedin", row)
    assert job.salary_min == 100 and job.salary_max == 120
    assert job.salary_period == "hourly"
    assert job.posted_at is None
    assert job.description is None


def test_handles_company_as_mapping():
    row = {"title": "Dev", "company": {"displayname": "ACME Corp"}, "job_url": "u"}
    job = row_to_job("glassdoor", row)
    assert job.company == "ACME Corp"
    assert job.source_display == "Glassdoor"


def test_provider_unconfigured_without_library(monkeypatch):
    provider = JobSpyProvider("linkedin")
    # Simulate jobspy not being installed.
    monkeypatch.setattr(JobSpyProvider, "library_available", staticmethod(lambda: False))
    assert provider.is_configured() is False
    assert "jobspy" in provider.not_configured_reason().lower()


def test_site_display_names():
    assert JobSpyProvider("zip_recruiter").display_name == "ZipRecruiter"
    assert JobSpyProvider("linkedin").name == "linkedin"
