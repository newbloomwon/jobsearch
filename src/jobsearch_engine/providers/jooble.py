"""Jooble — official free jobs API (https://jooble.org/api/about).

Key comes from their aggregator program; one POST per search.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional

import httpx

from ..models import Job, JobQuery
from .base import JobProvider, ProviderError

_API_URL = "https://jooble.org/api"

_SALARY_NUMBERS = re.compile(r"\$?\s*(\d[\d,.]*)([kK])?")


def parse_salary(text: str) -> tuple[Optional[float], Optional[float], Optional[str]]:
    """Parse strings like '$120k - $150k a year' / '$45 - $60/hr'."""
    if not text:
        return None, None, None
    values: list[float] = []
    for match in _SALARY_NUMBERS.finditer(text):
        raw = match.group(1).replace(",", "")
        try:
            value = float(raw)
        except ValueError:
            continue
        if match.group(2):  # 'k' suffix
            value *= 1000
        values.append(value)
    if not values:
        return None, None, None
    period = "hourly" if "/hr" in text or "hour" in text.lower() else "yearly"
    return min(values), max(values), period


class JoobleProvider(JobProvider):
    name = "jooble"
    display_name = "Jooble"

    def __init__(self, api_key: Optional[str] = None, client: Optional[httpx.AsyncClient] = None):
        self.api_key = (api_key or "").strip()
        self.client = client

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def not_configured_reason(self) -> str:
        return "Set JOOBLE_API_KEY (free at jooble.org/api/about)"

    async def search(self, query: JobQuery) -> list[Job]:
        payload: dict[str, Any] = {"keywords": query.keywords, "page": 1}
        if query.location:
            payload["location"] = query.location

        client = self.client or httpx.AsyncClient(timeout=20)
        try:
            try:
                resp = await client.post(f"{_API_URL}/{self.api_key}", json=payload)
            except httpx.HTTPError as exc:
                raise ProviderError(f"Jooble request failed: {exc}") from exc
        finally:
            if self.client is None:
                await client.aclose()

        if resp.status_code in (401, 403):
            raise ProviderError("Jooble rejected the API key (check JOOBLE_API_KEY)")
        if resp.status_code == 429:
            raise ProviderError("Jooble rate limit hit — retry in a minute")
        if resp.status_code != 200:
            raise ProviderError(f"Jooble returned HTTP {resp.status_code}")

        try:
            jobs = resp.json().get("jobs", [])
        except ValueError as exc:
            raise ProviderError("Jooble returned malformed JSON") from exc

        return [self._to_job(item) for item in jobs if item.get("title")]

    def _to_job(self, item: dict[str, Any]) -> Job:
        salary_min, salary_max, period = parse_salary(item.get("salary", ""))
        updated = str(item.get("updated", "") or item.get("date", ""))[:10]
        return Job(
            id=f"jooble:{item.get('id') or item.get('link')}",
            source=self.name,
            source_display=self.display_name,
            title=item.get("title", ""),
            company=item.get("company") or None,
            location=item.get("location") or None,
            url=item.get("link"),
            posted_at=date.fromisoformat(updated) if len(updated) == 10 else None,
            description=item.get("snippet") or None,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_period=period,
            extra={"salary_raw": item.get("salary"), "source_site": item.get("source")},
        )
