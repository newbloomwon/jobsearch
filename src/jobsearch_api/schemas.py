"""HTTP request/response schemas.

Deliberately decoupled from engine models: this is the public contract for
the frontend partner. Fields serialize as camelCase (frontend-friendly) and
accept snake_case too.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---------- Requests ----------

class SearchRequest(CamelModel):
    keywords: str = Field(..., min_length=2, description='e.g. "software engineer"')
    location: Optional[str] = None
    country: str = "USA"
    distance_mi: int = Field(50, ge=0, le=500)
    is_remote: bool = False
    job_type: Optional[str] = None  # fulltime | parttime | contract | internship
    hours_old: Optional[int] = Field(None, ge=1, le=720)
    results_wanted: int = Field(15, ge=1, le=50, description="per provider")
    providers: Optional[list[str]] = None
    resume_id: Optional[str] = None
    resume_text: Optional[str] = None
    min_score: Optional[float] = Field(None, ge=0, le=100)
    limit: int = Field(30, ge=1, le=100)


class ResumeTextRequest(CamelModel):
    text: str = Field(..., min_length=50)


# ---------- Responses ----------

class JobQueryOut(CamelModel):
    keywords: str
    location: Optional[str] = None
    country: str
    distance_mi: int
    is_remote: bool
    job_type: Optional[str] = None
    hours_old: Optional[int] = None
    results_wanted: int


class ScoreBreakdownOut(CamelModel):
    skills: float
    title: float
    seniority: float
    experience: float
    affinity: float
    matched_skills: list[str] = []
    missing_required_skills: list[str] = []
    matched_preferred_skills: list[str] = []
    reasons: list[str] = []


class ScoredJobOut(CamelModel):
    id: str
    source: str
    source_display: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None
    job_type: Optional[str] = None
    is_remote: bool = False
    posted_at: Optional[date] = None
    description: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_period: Optional[str] = None
    salary_currency: Optional[str] = None
    skills: list[str] = []
    extra: dict[str, Any] = {}
    score: float = 0.0
    breakdown: Optional[ScoreBreakdownOut] = None


class ProviderResultOut(CamelModel):
    provider: str
    display_name: str = ""
    status: str
    count: int = 0
    error: Optional[str] = None
    elapsed_ms: int = 0


class SearchResponseOut(CamelModel):
    query: JobQueryOut
    jobs: list[ScoredJobOut] = []
    providers: list[ProviderResultOut] = []
    duplicates_removed: int = 0
    scored: bool = False


class ResumeProfileOut(CamelModel):
    skills: list[str] = []
    titles: list[str] = []
    seniority: Optional[str] = None
    years_experience: Optional[float] = None
    education: Optional[str] = None
    char_count: int = 0


class ResumeUploadResponse(CamelModel):
    resume_id: str
    profile: ResumeProfileOut


class ProviderInfoOut(CamelModel):
    name: str
    display_name: str
    configured: bool
    setup_hint: Optional[str] = None


class HealthOut(CamelModel):
    status: str
    version: str
    providers_configured: int
    providers_total: int
