"""Thin HTTP layer over the jobsearch engine.

Every scrap of business logic lives in `jobsearch_engine`; this module only
translates HTTP <-> engine calls so the engine stays framework-agnostic.

Interactive API docs for the frontend partner: GET /docs
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from jobsearch_engine import (
    JobQuery,
    ResumeParseError,
    build_profile,
    build_registry,
    extract_text,
    search,
)
from jobsearch_engine import __version__ as engine_version
from jobsearch_engine.providers import Settings

from .schemas import (
    HealthOut,
    ProviderInfoOut,
    ResumeProfileOut,
    ResumeTextRequest,
    ResumeUploadResponse,
    SearchRequest,
    SearchResponseOut,
)
from .store import ResumeStore

_STATIC_DIR = Path(__file__).parent / "static"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def create_app() -> FastAPI:
    settings = Settings.from_env()
    registry = build_registry(settings)
    store = ResumeStore(ttl_seconds=_env_int("JOBSEARCH_RESUME_TTL_HOURS", 24) * 3600)
    provider_timeout = float(_env_int("JOBSEARCH_PROVIDER_TIMEOUT", 60))

    origins_raw = os.environ.get("JOBSEARCH_ALLOWED_ORIGINS", "*").strip()
    origins = ["*"] if origins_raw == "*" else [o.strip() for o in origins_raw.split(",") if o.strip()]

    app = FastAPI(
        title="JobSearch Engine API",
        description=(
            "Aggregates job listings across platforms and scores them against an "
            "uploaded resume. POST /api/resume once, then POST /api/jobs/search "
            "with the returned resumeId."
        ),
        version=engine_version,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- health & provider discovery -------------------------------------

    @app.get("/healthz", response_model=HealthOut, tags=["meta"])
    async def healthz() -> HealthOut:
        configured = [p for p in registry.values() if p.is_configured()]
        return HealthOut(
            status="ok",
            version=engine_version,
            providers_configured=len(configured),
            providers_total=len(registry),
        )

    @app.get("/api/providers", response_model=list[ProviderInfoOut], tags=["meta"])
    async def list_providers() -> list[ProviderInfoOut]:
        return [
            ProviderInfoOut(
                name=provider.name,
                display_name=provider.display_name,
                configured=provider.is_configured(),
                setup_hint=None if provider.is_configured() else provider.not_configured_reason(),
            )
            for provider in registry.values()
        ]

    # ---- resume upload ----------------------------------------------------

    @app.post(
        "/api/resume",
        response_model=ResumeUploadResponse,
        tags=["resume"],
        summary="Upload a resume file (PDF/DOCX/TXT) and get a resumeId + parsed profile",
    )
    async def upload_resume(
        file: UploadFile | None = File(None), text: str | None = Form(None)
    ) -> ResumeUploadResponse:
        raw = None
        if file is not None:
            raw = await file.read()
        if not raw and not (text and text.strip()):
            raise HTTPException(400, "Attach a resume file (multipart 'file') or plain text (form 'text')")

        try:
            resume_text = extract_text(file.filename if file else "", raw) if raw else text  # type: ignore[assignment]
            profile = build_profile(resume_text)
        except ResumeParseError as exc:
            raise HTTPException(400, str(exc)) from exc

        resume_id = store.save(profile)
        return ResumeUploadResponse(
            resume_id=resume_id,
            profile=ResumeProfileOut(**profile.model_dump(exclude={"tokens"})),
        )

    @app.post(
        "/api/resume/text",
        response_model=ResumeUploadResponse,
        tags=["resume"],
        summary="Paste resume text directly",
    )
    async def upload_resume_text(body: ResumeTextRequest) -> ResumeUploadResponse:
        profile = build_profile(body.text)
        resume_id = store.save(profile)
        return ResumeUploadResponse(
            resume_id=resume_id,
            profile=ResumeProfileOut(**profile.model_dump(exclude={"tokens"})),
        )

    # ---- search -----------------------------------------------------------

    @app.post(
        "/api/jobs/search",
        response_model=SearchResponseOut,
        tags=["jobs"],
        summary="Search every provider, dedupe, and score against the resume",
    )
    async def search_jobs(request: SearchRequest) -> SearchResponseOut:
        profile = None
        if request.resume_id:
            profile = store.get(request.resume_id)
            if profile is None:
                raise HTTPException(404, f"resumeId '{request.resume_id}' not found or expired")
        elif request.resume_text:
            profile = build_profile(request.resume_text)

        query = JobQuery(
            keywords=request.keywords,
            location=request.location,
            country=request.country,
            distance_mi=request.distance_mi,
            is_remote=request.is_remote,
            job_type=request.job_type,
            hours_old=request.hours_old,
            results_wanted=request.results_wanted,
        )

        result = await search(
            query,
            registry=registry,
            requested=request.providers,
            profile=profile,
            limit=request.limit,
            timeout_s=provider_timeout,
        )

        jobs = result.jobs
        if request.min_score is not None:
            jobs = [job for job in jobs if job.score >= request.min_score]

        return SearchResponseOut.model_validate(
            {**result.model_dump(), "jobs": [job.model_dump() for job in jobs]},
            from_attributes=True,
        )

    # ---- placeholder frontend (partner replaces this) ---------------------
    if _STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="placeholder-ui")

    return app


app = create_app()
