"""Adzuna — official free-tier jobs API (https://developer.adzuna.com).

Aggregates postings from many boards and works reliably from datacenter IPs,
which makes it a dependable fallback when scraped boards rate-limit us.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

import httpx

from ..models import Job, JobQuery
from .base import JobProvider, ProviderError

_API_URL = "https://api.adzuna.com/v1/api/jobs"

# jobspy-style country name -> Adzuna country code
_COUNTRIES = {
    "usa": "us",
    "united states": "us",
    "uk": "uk",
    "united kingdom": "uk",
    "canada": "ca",
    "australia": "au",
    "germany": "de",
    "france": "fr",
    "india": "in",
    "brazil": "br",
    "netherlands": "nl",
    "poland": "pl",
    "austria": "at",
    "switzerland": "ch",
    "spain": "es",
    "italy": "it",
    "mexico": "mx",
    "singapore": "sg",
    "south africa": "za",
}


class AdzunaProvider(JobProvider):
    name = "adzuna"
    display_name = "Adzuna"

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.app_id = (app_id or "").strip()
        self.app_key = (app_key or "").strip()
        self.client = client

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_key)

    def not_configured_reason(self) -> str:
        return "Set ADZUNA_APP_ID and ADZUNA_APP_KEY (free at developer.adzuna.com)"

    async def search(self, query: JobQuery) -> list[Job]:
        country = _COUNTRIES.get(query.country.lower().strip(), query.country.lower().strip())
        params: dict[str, Any] = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": query.keywords,
            "results_per_page": min(query.results_wanted, 50),
            "content-type": "application/json",
        }
        if query.location:
            params["where"] = query.location
            params["distance"] = query.distance_mi
        if query.is_remote:
            params["remote"] = 1  # undocumented but harmless if ignored

        client = self.client or httpx.AsyncClient(timeout=20)
        try:
            try:
                resp = await client.get(f"{_API_URL}/{country}/search/1", params=params)
            except httpx.HTTPError as exc:
                raise ProviderError(f"Adzuna request failed: {exc}") from exc
        finally:
            if self.client is None:
                await client.aclose()

        if resp.status_code in (401, 403):
            raise ProviderError("Adzuna rejected the credentials (check ADZUNA_APP_ID/KEY)")
        if resp.status_code == 429:
            raise ProviderError("Adzuna rate limit hit — retry in a minute")
        if resp.status_code != 200:
            raise ProviderError(f"Adzuna returned HTTP {resp.status_code}")

        try:
            results = resp.json().get("results", [])
        except ValueError as exc:
            raise ProviderError("Adzuna returned malformed JSON") from exc

        return [self._to_job(item) for item in results if item.get("title")]

    def _to_job(self, item: dict[str, Any]) -> Job:
        company = (item.get("company") or {}).get("displayname")
        location = (item.get("location") or {}).get("displayname")
        created = str(item.get("created", ""))[:10]
        contract_type = (item.get("contract_type") or "").replace("_", "")
        return Job(
            id=f"adzuna:{item.get('id')}",
            source=self.name,
            source_display=self.display_name,
            title=item.get("title", ""),
            company=company,
            location=location,
            url=item.get("redirect_url"),
            job_type=contract_type or None,
            is_remote="remote" in str(item.get("title", "")).lower()
            or "remote" in str(item.get("location", {}).get("displayname", "")).lower(),
            posted_at=date.fromisoformat(created) if len(created) == 10 else None,
            description=item.get("description"),
            salary_min=item.get("salary_min"),
            salary_max=item.get("salary_max"),
            salary_period="yearly",
            salary_currency=item.get("currency") or (
                "USD" if str(item.get("redirect_url", "")).find("adzuna.com/us") >= 0 else None
            ),
            extra={
                "category": (item.get("category") or {}).get("label"),
                "contract_time": item.get("contract_time"),
            },
        )
