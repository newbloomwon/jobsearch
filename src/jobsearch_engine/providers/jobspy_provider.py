"""LinkedIn / Indeed / Glassdoor / ZipRecruiter via the OSS JobSpy library.

JobSpy (https://github.com/speedyapply/JobSpy, `pip install python-jobspy`)
scrapes these boards concurrently and returns a pandas DataFrame. The library
is an optional dependency (`scrapers` extra): when it isn't installed the
provider reports itself as not configured and the search degrades gracefully.

Field mapping lives in `row_to_job`, which works on any Mapping so it is
unit-testable without pandas or network access.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any, Mapping, Optional

from ..models import Job, JobQuery
from .base import JobProvider, ProviderError

_SITE_DISPLAY = {
    "linkedin": "LinkedIn",
    "indeed": "Indeed",
    "glassdoor": "Glassdoor",
    "zip_recruiter": "ZipRecruiter",
    "google": "Google Jobs",
}


def _first(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row.get(key) is not None:
            return row.get(key)
    return None


def _to_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    # pandas missing values leak through as NaN/inf; treat them as absent.
    if result != result or result in (float("inf"), float("-inf")):
        return None
    return result


def row_to_job(site: str, row: Mapping[str, Any]) -> Job:
    """Map one JobSpy DataFrame row to a normalized Job."""
    compensation = row.get("compensation") if isinstance(row.get("compensation"), Mapping) else {}
    url = _first(row, "job_url", "job_url_hyper", "url")
    location = _first(row, "location") or " ".join(
        str(part) for part in [_first(row, "city"), _first(row, "state")] if part
    )
    raw_company = _first(row, "company")
    if isinstance(raw_company, Mapping):
        raw_company = raw_company.get("displayname")
    company = str(raw_company) if raw_company else None
    salary_min = _to_float(_first(row, "min_amount") or compensation.get("min_amount"))
    salary_max = _to_float(_first(row, "max_amount") or compensation.get("max_amount"))
    period = _first(row, "interval") or compensation.get("interval")
    currency = _first(row, "currency") or compensation.get("currency")
    return Job(
        id=f"{site}:{_first(row, 'id', 'job_url_hyper', 'job_url') or row.get('title', '')}",
        source=site,
        source_display=_SITE_DISPLAY.get(site, site.title()),
        title=str(_first(row, "title") or "Untitled role"),
        company=company,
        location=str(location) if location else None,
        url=str(url) if url else None,
        job_type=(
            str(row.get("job_type")).lower() if row.get("job_type") not in (None, "") else None
        ),
        is_remote=bool(row.get("is_remote")),
        posted_at=_to_date(_first(row, "date_posted", "date")),
        description=_first(row, "description"),
        salary_min=salary_min,
        salary_max=salary_max,
        salary_period=str(period).lower() if period else None,
        salary_currency=str(currency or "USD"),
        extra={
            k: str(v)
            for k, v in (
                ("job_level", row.get("job_level")),
                ("job_function", row.get("job_function")),
                ("company_industry", row.get("company_industry")),
                ("company_url", row.get("company_url_direct") or row.get("company_url")),
                ("salary_source", _first(row, "salary_source") or compensation.get("salary_source")),
            )
            if v not in (None, "")
        },
    )


class JobSpyProvider(JobProvider):
    """One scraped board backed by JobSpy (site_name: linkedin/indeed/...)."""

    def __init__(self, site: str, proxies: Optional[list[str]] = None):
        self.site = site
        self.display_name = _SITE_DISPLAY.get(site, site.title())
        self.proxies = proxies
        self.name = site

    @staticmethod
    def library_available() -> bool:
        try:
            import jobspy  # noqa: F401
        except ImportError:
            return False
        return True

    def is_configured(self) -> bool:
        return self.library_available()

    def not_configured_reason(self) -> str:
        return "python-jobspy is not installed — pip install '.[scrapers]'"

    async def search(self, query: JobQuery) -> list[Job]:
        from jobspy import scrape_jobs  # lazy: optional dependency

        kwargs: dict[str, Any] = {
            "site_name": [self.site],
            "search_term": query.keywords,
            "results_wanted": query.results_wanted,
            "country_indeed": query.country,
            "verbose": 0,
        }
        if query.location:
            kwargs["location"] = query.location
            kwargs["distance"] = query.distance_mi
        if query.hours_old:
            kwargs["hours_old"] = query.hours_old
        if query.job_type:
            kwargs["job_type"] = query.job_type
        if query.is_remote:
            kwargs["is_remote"] = True
        if self.site == "linkedin":
            # Descriptions cost one extra request per job but make scoring
            # far better; LinkedIn tolerates it at hackathon volumes.
            kwargs["linkedin_fetch_description"] = True
        if self.proxies:
            kwargs["proxies"] = self.proxies

        try:
            df = await asyncio.to_thread(scrape_jobs, **kwargs)
        except Exception as exc:
            raise ProviderError(f"{self.display_name} scrape failed: {exc}") from exc
        if df is None or df.empty:
            return []
        return [row_to_job(self.site, row) for _, row in df.iterrows()]
