"""Offline sample data provider.

Deterministic, no network — lets the frontend be built/demoed without live
scrapers or API keys. Enable by requesting provider "sample" explicitly, or
set JOBSEARCH_SAMPLE=1 to include it in default searches.
"""
from __future__ import annotations

from datetime import date

from ..models import Job, JobQuery
from .base import JobProvider

_TODAY = date(2026, 8, 19)

_SAMPLE_JOBS: list[dict] = [
    {
        "id": "sample:1",
        "title": "Senior Backend Engineer (Python/Go)",
        "company": "Northwind Labs",
        "location": "New York, NY",
        "url": "https://example.com/jobs/1",
        "job_type": "fulltime",
        "is_remote": False,
        "posted_at": "2026-08-18",
        "salary_min": 165000,
        "salary_max": 210000,
        "salary_period": "yearly",
        "description": (
            "Own critical services on our payments platform.\n"
            "Requirements: 5+ years building production backends with Python and Go. "
            "Strong SQL and PostgreSQL experience. Deep knowledge of REST API design, "
            "Docker and Kubernetes.\n"
            "Nice to have: Kafka, Terraform, AWS certification."
        ),
    },
    {
        "id": "sample:2",
        "title": "Frontend Engineer — React/TypeScript",
        "company": "Brightfolio",
        "location": "Remote (US)",
        "url": "https://example.com/jobs/2",
        "job_type": "fulltime",
        "is_remote": True,
        "posted_at": "2026-08-17",
        "salary_min": 130000,
        "salary_max": 170000,
        "salary_period": "yearly",
        "description": (
            "Build delightful dashboards used by 2M designers.\n"
            "Requirements: 3+ years with React, TypeScript, JavaScript and CSS. "
            "Experience with Jest and Cypress testing. Nice to have: Next.js, "
            "GraphQL, Storybook."
        ),
    },
    {
        "id": "sample:3",
        "title": "Data Scientist, Machine Learning",
        "company": "Meridian Health AI",
        "location": "Boston, MA",
        "url": "https://example.com/jobs/3",
        "job_type": "fulltime",
        "is_remote": False,
        "posted_at": "2026-08-16",
        "salary_min": 145000,
        "salary_max": 185000,
        "salary_period": "yearly",
        "description": (
            "Train models that improve patient outcomes.\n"
            "Requirements: Python, pandas, scikit-learn, PyTorch, machine learning "
            "and NLP experience, 4+ years. SQL and statistics required.\n"
            "Bonus: MLflow, Kubernetes, llm fine-tuning, A/B testing."
        ),
    },
    {
        "id": "sample:4",
        "title": "Software Engineer Intern — Summer 2027",
        "company": "Cobalt Systems",
        "location": "Seattle, WA",
        "url": "https://example.com/jobs/4",
        "job_type": "internship",
        "is_remote": False,
        "posted_at": "2026-08-15",
        "salary_min": 42,
        "salary_max": 52,
        "salary_period": "hourly",
        "description": (
            "Join our platform team for a 12-week internship. Currently enrolled students only.\n"
            "Requirements: coursework in Python or Java, git basics, curiosity.\n"
            "Nice to have: Docker, unit testing, SQL."
        ),
    },
    {
        "id": "sample:5",
        "title": "Full Stack Developer (Node.js/React)",
        "company": "Trailblaze Fitness",
        "location": "Austin, TX",
        "url": "https://example.com/jobs/5",
        "job_type": "fulltime",
        "is_remote": True,
        "posted_at": "2026-08-14",
        "salary_min": 120000,
        "salary_max": 150000,
        "salary_period": "yearly",
        "description": (
            "Ship features across our whole stack.\n"
            "Requirements: Node.js, Express, React, PostgreSQL, REST APIs, 3+ years. "
            "Comfortable with AWS and Docker.\nPreferred: TypeScript, GraphQL, Redis."
        ),
    },
    {
        "id": "sample:6",
        "title": "DevOps Engineer / SRE",
        "company": "Gridline Infrastructure",
        "location": "Denver, CO",
        "url": "https://example.com/jobs/6",
        "job_type": "fulltime",
        "is_remote": False,
        "posted_at": "2026-08-13",
        "salary_min": 150000,
        "salary_max": 190000,
        "salary_period": "yearly",
        "description": (
            "Keep our energy-analytics platform reliable at scale.\n"
            "Requirements: Linux, Kubernetes, Terraform, CI/CD pipelines, AWS, "
            "Prometheus and Grafana monitoring, 5+ years.\nNice to have: Go, Helm, Datadog."
        ),
    },
    {
        "id": "sample:7",
        "title": "Data Engineer",
        "company": "Acme Analytics",
        "location": "New York, NY",
        "url": "https://example.com/jobs/7",
        "job_type": "fulltime",
        "is_remote": False,
        "posted_at": "2026-08-12",
        "salary_min": 140000,
        "salary_max": 175000,
        "salary_period": "yearly",
        "description": (
            "Build the pipelines feeding our ML platform.\n"
            "Requirements: Python, SQL, Spark, Airflow, dbt, Snowflake, 4+ years.\n"
            "Preferred: Kafka, AWS, Terraform."
        ),
    },
    {
        # Duplicate of sample:7 — same role surfaced by a second board.
        "id": "sample:7b",
        "title": "Data Engineer",
        "company": "Acme Analytics Inc.",
        "location": "New York, NY (Hybrid)",
        "url": "https://example.com/jobs/7b",
        "job_type": "fulltime",
        "is_remote": False,
        "posted_at": "2026-08-12",
        "salary_min": 140000,
        "salary_max": 175000,
        "salary_period": "yearly",
        "description": (
            "Build the pipelines feeding our ML platform. Requirements: Python, SQL, "
            "Spark, Airflow, dbt, Snowflake, 4+ years. Preferred: Kafka, AWS."
        ),
    },
    {
        "id": "sample:8",
        "title": "Campus Recruiting Coordinator",
        "company": "State University Career Center",
        "location": "Tampa, FL",
        "url": "https://example.com/jobs/8",
        "job_type": "fulltime",
        "is_remote": False,
        "posted_at": "2026-08-11",
        "salary_min": 48000,
        "salary_max": 56000,
        "salary_period": "yearly",
        "description": (
            "Coordinate career fairs and campus interviews in Handshake.\n"
            "Requirements: 1+ years program coordination, Excel, strong communication. "
            "Nice to have: Jira, SQL."
        ),
    },
    {
        "id": "sample:9",
        "title": "Mobile Engineer (iOS, Swift)",
        "company": "Larkspur Media",
        "location": "Remote (Worldwide)",
        "url": "https://example.com/jobs/9",
        "job_type": "contract",
        "is_remote": True,
        "posted_at": "2026-08-10",
        "salary_min": 80,
        "salary_max": 110,
        "salary_period": "hourly",
        "description": (
            "Craft our flagship iOS app.\n"
            "Requirements: Swift, iOS SDK, 4+ years shipping App Store apps, "
            "unit testing discipline.\nPreferred: SwiftUI, GraphQL, Firebase."
        ),
    },
    {
        "id": "sample:10",
        "title": "Product Manager, Growth",
        "company": "Fable & Fern",
        "location": "San Francisco, CA",
        "url": "https://example.com/jobs/10",
        "job_type": "fulltime",
        "is_remote": False,
        "posted_at": "2026-08-09",
        "salary_min": 155000,
        "salary_max": 185000,
        "salary_period": "yearly",
        "description": (
            "Drive activation and retention for our consumer app.\n"
            "Requirements: 4+ years product management, SQL, A/B testing, "
            "agile ceremonies, Figma fluency.\nBonus: Python, Looker, ux research."
        ),
    },
    {
        "id": "sample:11",
        "title": "Junior QA Analyst",
        "company": "Beacon Retail Group",
        "location": "Chicago, IL",
        "url": "https://example.com/jobs/11",
        "job_type": "fulltime",
        "is_remote": False,
        "posted_at": "2026-08-08",
        "salary_min": 65000,
        "salary_max": 80000,
        "salary_period": "yearly",
        "description": (
            "Manual + automated testing for our e-commerce platform.\n"
            "Requirements: Selenium, Jira, 1+ years QA, sharp eye for detail.\n"
            "Nice to have: Cypress, Python, SQL."
        ),
    },
    {
        "id": "sample:12",
        "title": "Staff Software Engineer, Platform",
        "company": "Northwind Labs",
        "location": "Remote (US)",
        "url": "https://example.com/jobs/12",
        "job_type": "fulltime",
        "is_remote": True,
        "posted_at": "2026-08-07",
        "salary_min": 220000,
        "salary_max": 270000,
        "salary_period": "yearly",
        "description": (
            "Lead the platform team building our internal developer experience.\n"
            "Requirements: 8+ years, deep Go and Kubernetes expertise, distributed "
            "systems, microservices, gRPC, Kafka.\nPreferred: Rust, Terraform, Helm."
        ),
    },
]


def _matches(job: dict, query: JobQuery) -> bool:
    haystack = f"{job['title']} {job['company']} {job['description']}".lower()
    if query.keywords.strip():
        tokens = [t for t in query.keywords.lower().split() if len(t) > 2]
        if tokens and not any(t in haystack for t in tokens):
            return False
    if query.location and query.location.strip():
        if not any(
            t in f"{job['location']}".lower() or job["is_remote"]
            for t in query.location.lower().split(",")
        ):
            return False
    if query.is_remote and not job["is_remote"]:
        return False
    if query.job_type and job["job_type"] != query.job_type:
        return False
    if query.hours_old:
        posted = date.fromisoformat(job["posted_at"])
        if (_TODAY - posted).days > query.hours_old // 24 + 1:
            return False
    return True


class SampleProvider(JobProvider):
    name = "sample"
    display_name = "Sample Data"

    def is_configured(self) -> bool:
        return True

    def not_configured_reason(self) -> str:  # pragma: no cover
        return ""

    async def search(self, query: JobQuery) -> list[Job]:
        jobs = [
            Job(
                source=self.name,
                source_display=self.display_name,
                **{**row, "posted_at": date.fromisoformat(row["posted_at"])},
            )
            for row in _SAMPLE_JOBS
            if _matches(row, query)
        ]
        return jobs[: query.results_wanted]
