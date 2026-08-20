"""Core data models for the jobsearch engine.

Pure pydantic — no web-framework imports anywhere in this package, so the
engine can be embedded in FastAPI, Flask, a CLI, or a batch job.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field


class Job(BaseModel):
    """A normalized job listing from any provider."""

    id: str
    source: str  # provider name, e.g. "linkedin"
    source_display: str = ""  # human label, e.g. "LinkedIn"
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None
    job_type: Optional[str] = None  # fulltime / parttime / contract / internship
    is_remote: bool = False
    posted_at: Optional[date] = None
    description: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_period: Optional[str] = None  # yearly / monthly / hourly ...
    salary_currency: Optional[str] = None
    # Detected at ingestion time by the skills module.
    skills: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class JobQuery(BaseModel):
    """What to search for on each platform."""

    keywords: str
    location: Optional[str] = None
    country: str = "USA"  # jobspy-style country name for Indeed/Glassdoor
    distance_mi: int = 50
    is_remote: bool = False
    job_type: Optional[str] = None  # fulltime / parttime / contract / internship
    hours_old: Optional[int] = None
    results_wanted: int = 15  # per provider


class ScoreBreakdown(BaseModel):
    """Per-component detail behind a job's match score (great UI fodder)."""

    skills: float  # 0..1 overlap of job skills with resume skills
    title: float  # 0..1 similarity of job title to resume titles
    seniority: float  # 0..1 seniority-level alignment
    experience: float  # 0..1 years-of-experience fit
    affinity: float  # 0..1 overall text similarity
    matched_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    matched_preferred_skills: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class ScoredJob(Job):
    score: float = 0.0  # 0..100
    breakdown: Optional[ScoreBreakdown] = None


class ProviderResult(BaseModel):
    """Outcome of one provider in a search (success, failure, or skipped)."""

    provider: str
    display_name: str = ""
    status: str = "ok"  # ok | error | not_configured | timeout
    count: int = 0
    error: Optional[str] = None
    elapsed_ms: int = 0


class SearchResponse(BaseModel):
    query: JobQuery
    jobs: list[ScoredJob] = Field(default_factory=list)
    providers: list[ProviderResult] = Field(default_factory=list)
    duplicates_removed: int = 0
    scored: bool = False


class ResumeProfile(BaseModel):
    """Structured signals extracted from a resume."""

    skills: list[str] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)
    seniority: Optional[str] = None  # intern | junior | mid | senior | staff | principal
    years_experience: Optional[float] = None
    education: Optional[str] = None  # phd | master | bachelor | associate
    char_count: int = 0
    tokens: dict[str, int] = Field(default_factory=dict)
