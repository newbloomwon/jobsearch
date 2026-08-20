#!/usr/bin/env python3
"""Live end-to-end smoke test for the scraped providers (LinkedIn/Indeed/...).

Hits the real boards once — expects `pip install '.[scrapers]'`. Use this to
verify scraping works from your network/deploy region before a demo:

    python scripts/smoke_jobspy.py "python developer" "New York, NY"
"""
from __future__ import annotations

import asyncio
import sys

from jobsearch_engine import JobQuery, search
from jobsearch_engine.providers import build_registry


async def main() -> int:
    keywords = sys.argv[1] if len(sys.argv) > 1 else "software engineer"
    location = sys.argv[2] if len(sys.argv) > 2 else None

    registry = build_registry()
    result = await search(
        JobQuery(keywords=keywords, location=location, results_wanted=8),
        registry,
        requested=["linkedin", "indeed", "glassdoor"],
        timeout_s=180.0,
    )

    print("\n=== provider status ===")
    for p in result.providers:
        line = f"{p.provider:12} {p.status:14} {p.count:3} jobs  {p.elapsed_ms}ms"
        if p.error:
            line += f"\n             └─ {p.error}"
        print(line)

    print(f"\n=== {len(result.jobs)} unique jobs (deduped {result.duplicates_removed}) ===")
    for job in result.jobs[:10]:
        salary = ""
        if job.salary_min:
            salary = f"  ${job.salary_min:,.0f}"
            if job.salary_max and job.salary_max != job.salary_min:
                salary += f"-${job.salary_max:,.0f}"
        print(f"[{job.source:9}] {job.title[:45]:45} @ {(job.company or '?')[:22]:22}{salary}")
        print(f"            {job.url}")

    ok = sum(p.count for p in result.providers if p.status == "ok")
    return 0 if ok or result.jobs else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
