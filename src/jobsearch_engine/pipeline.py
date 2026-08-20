"""Search orchestration: fan out to providers → normalize → dedupe → score."""
from __future__ import annotations

import asyncio
import time

from .models import Job, JobQuery, ProviderResult, ResumeProfile, ScoredJob, SearchResponse
from .providers.base import JobProvider, ProviderError
from .scoring import analyze_job, score_job
from .dedupe import dedupe_jobs


async def _run_provider(
    provider: JobProvider, query: JobQuery, timeout_s: float
) -> tuple[ProviderResult, list[Job]]:
    started = time.monotonic()
    try:
        if not provider.is_configured():
            result = ProviderResult(
                provider=provider.name,
                display_name=provider.display_name,
                status="not_configured",
                error=provider.not_configured_reason(),
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
            return result, []
        jobs = await asyncio.wait_for(provider.search(query), timeout=timeout_s)
        return (
            ProviderResult(
                provider=provider.name,
                display_name=provider.display_name,
                status="ok",
                count=len(jobs),
                elapsed_ms=int((time.monotonic() - started) * 1000),
            ),
            jobs,
        )
    except asyncio.TimeoutError:
        return (
            ProviderResult(
                provider=provider.name,
                display_name=provider.display_name,
                status="timeout",
                error=f"Timed out after {timeout_s:.0f}s",
                elapsed_ms=int((time.monotonic() - started) * 1000),
            ),
            [],
        )
    except ProviderError as exc:
        return (
            ProviderResult(
                provider=provider.name,
                display_name=provider.display_name,
                status="error",
                error=str(exc),
                elapsed_ms=int((time.monotonic() - started) * 1000),
            ),
            [],
        )
    except Exception as exc:  # defensive: one provider must not kill the search
        return (
            ProviderResult(
                provider=provider.name,
                display_name=provider.display_name,
                status="error",
                error=f"{type(exc).__name__}: {exc}",
                elapsed_ms=int((time.monotonic() - started) * 1000),
            ),
            [],
        )


async def search(
    query: JobQuery,
    registry: dict[str, JobProvider],
    requested: list[str] | None = None,
    profile: ResumeProfile | None = None,
    limit: int = 30,
    timeout_s: float = 60.0,
) -> SearchResponse:
    """Aggregate jobs across providers, dedupe, optionally score, rank.

    Default provider set: everything configured except "sample", which only
    joins the default set as a last-resort fallback when no real provider is
    usable (callers can always request it explicitly).
    """
    if requested is None:
        configured = [name for name, provider in registry.items() if provider.is_configured()]
        names = [name for name in configured if name != "sample"] or ["sample"]
    else:
        names = requested

    outcomes = await asyncio.gather(
        *(
            _run_provider(registry[name], query, timeout_s)
            if name in registry
            else _unknown_provider(name)
            for name in names
        )
    )

    provider_results = [outcome[0] for outcome in outcomes]
    all_jobs: list[Job] = [job for outcome in outcomes for job in outcome[1]]

    deduped, removed = dedupe_jobs(all_jobs)

    if profile is not None:
        scored = [score_job(analyze_job(job), profile) for job in deduped]
        scored.sort(key=lambda j: (-j.score, j.title.lower()))
        jobs: list[Job] = scored
    else:
        analyzed = [analyze_job(job) for job in deduped]
        # Most recent first; jobs without a date sort last.
        analyzed.sort(key=lambda j: j.posted_at.toordinal() if j.posted_at else 0, reverse=True)
        jobs = [ScoredJob(**job.model_dump()) for job in analyzed]

    return SearchResponse(
        query=query,
        jobs=jobs[:limit],
        providers=provider_results,
        duplicates_removed=removed,
        scored=profile is not None,
    )


async def _unknown_provider(name: str) -> tuple[ProviderResult, list[Job]]:
    return (
        ProviderResult(
            provider=name,
            status="error",
            error=f"Unknown provider '{name}'",
        ),
        [],
    )
