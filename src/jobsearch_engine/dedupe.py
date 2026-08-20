"""Cross-provider deduplication.

The same role is often listed on LinkedIn, Indeed and Glassdoor at once. We
merge on (normalized company + normalized title) or identical URLs, keeping
the record with the richest description and recording where else it appeared.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from .models import Job

_COMPANY_SUFFIXES = re.compile(
    r"\b(inc|inc\.|llc|ltd|ltd\.|corp|corp\.|corporation|co|co\.|company|"
    r"technologies|technology|tech|labs|group|solutions|systems|gmbh|plc)\b",
    re.IGNORECASE,
)


def _norm(text: str | None) -> str:
    if not text:
        return ""
    lowered = text.lower()
    lowered = _COMPANY_SUFFIXES.sub(" ", lowered)
    return re.sub(r"[^a-z0-9]+", "", lowered)


def _url_key(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    # Strip tracking params — same path on the same host = same posting.
    return f"{parts.netloc.lower().removeprefix('www.')}{parts.path.rstrip('/')}"


def dedupe_jobs(jobs: list[Job]) -> tuple[list[Job], int]:
    """Merge duplicate postings. Returns (deduped_jobs, removed_count)."""
    by_url: dict[str, Job] = {}
    by_role: dict[str, Job] = {}
    removed = 0

    for job in jobs:
        url_key = _url_key(job.url)
        role_key = f"{_norm(job.company)}|{_norm(job.title)}"

        url_dup = by_url.get(url_key) if url_key else None
        role_dup = by_role.get(role_key) if role_key else None
        existing = url_dup or role_dup

        if existing is None:
            if url_key:
                by_url[url_key] = job
            by_role[role_key] = job
            continue

        removed += 1
        # Keep whichever record carries more information (description length,
        # then salary, then any URL at all).
        def richness(j: Job) -> tuple[int, int, int]:
            return (
                len(j.description or ""),
                1 if (j.salary_min or j.salary_max) else 0,
                1 if j.url else 0,
            )

        if richness(job) > richness(existing):
            winner, loser = job, existing
            winner.extra = {
                **loser.extra,
                **winner.extra,
                "also_found_on": sorted(
                    source
                    for source in {
                        loser.source,
                        *loser.extra.get("also_found_on", []),
                        winner.source,
                    }
                    if source != winner.source
                ),
            }
            if url_key:
                by_url[url_key] = winner
            by_role[role_key] = winner
        else:
            existing.extra.setdefault("also_found_on", [])
            if job.source not in existing.extra["also_found_on"] and job.source != existing.source:
                existing.extra["also_found_on"].append(job.source)

    # One job may sit in both dicts; collect unique identities by role key.
    seen: set[str] = set()
    unique: list[Job] = []
    for job in by_role.values():
        key = f"{_norm(job.company)}|{_norm(job.title)}|{job.url}"
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique, removed
