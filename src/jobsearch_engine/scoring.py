"""Resume ↔ job matching.

`score_job` produces a 0-100 score as a weighted blend of five components,
each returned individually so the frontend can show *why* a job matched:
skills overlap (50%), title similarity (20%), seniority alignment (10%),
years-of-experience fit (10%), and overall text affinity (10%).

All heuristics are deterministic and dependency-light (rapidfuzz for titles,
plain cosine over token counts for affinity) — no LLM calls required.
"""
from __future__ import annotations

import math
from typing import Optional

from rapidfuzz import fuzz

from .models import Job, ResumeProfile, ScoreBreakdown, ScoredJob
from .resume.profile import detect_seniority, detect_years, tokenize
from .skills import detect_skills_detailed

WEIGHTS = {
    "skills": 0.5,
    "title": 0.2,
    "seniority": 0.1,
    "experience": 0.1,
    "affinity": 0.1,
}

_SENIORITY_LADDER = ["intern", "junior", "mid", "senior", "staff", "principal"]
_NEUTRAL = 0.5


def analyze_job(job: Job) -> Job:
    """Detect skills on a job in place (skills + required/preferred in extra)."""
    text_parts = [job.title, job.company or "", job.description or ""]
    required, preferred = detect_skills_detailed(" \n ".join(text_parts))
    job.skills = sorted(set(required) | set(preferred))
    job.extra["required_skills"] = sorted(required)
    job.extra["preferred_skills"] = sorted(preferred)
    return job


def _skills_component(job: Job, profile: ResumeProfile) -> tuple[float, list[str], list[str], list[str]]:
    required = set(job.extra.get("required_skills") or [])
    preferred = set(job.extra.get("preferred_skills") or [])
    if not required and not preferred:
        # Undifferentiated skill list (no required/preferred signal): treat
        # everything as required rather than double-counting below.
        required = set(job.skills)
        preferred = set()

    resume = set(profile.skills)

    if not required and not preferred:
        return _NEUTRAL, [], [], []

    matched_required = sorted(required & resume)
    matched_preferred = sorted(preferred & resume)
    missing_required = sorted(required - resume)

    total_weight = 2.0 * len(required) + 1.0 * len(preferred)
    gained = 2.0 * len(matched_required) + 1.0 * len(matched_preferred)
    score = gained / total_weight if total_weight else _NEUTRAL
    return score, matched_required, missing_required, matched_preferred


def _title_component(job_title: str, profile: ResumeProfile) -> float:
    titles = profile.titles[:3]
    if not titles:
        return _NEUTRAL
    best = max(fuzz.token_set_ratio(job_title, t) for t in titles)
    return min(best / 100.0, 1.0)


def _seniority_component(job: Job, profile: ResumeProfile) -> tuple[float, Optional[str]]:
    job_tier = detect_seniority(job.title) or detect_seniority(job.description or "")
    profile_tier = profile.seniority
    if job_tier is None or profile_tier is None:
        return 0.7, job_tier
    distance = abs(_SENIORITY_LADDER.index(job_tier) - _SENIORITY_LADDER.index(profile_tier))
    if distance == 0:
        return 1.0, job_tier
    if distance == 1:
        return 0.6, job_tier
    return 0.3, job_tier


def _experience_component(job: Job, profile: ResumeProfile) -> tuple[float, Optional[float]]:
    min_years = detect_years(job.description or "") or detect_years(job.title)
    years = profile.years_experience
    if min_years is None or years is None:
        return 0.7, min_years
    deficit = min_years - years
    if deficit <= 0:
        return 1.0, min_years
    if deficit <= 1:
        return 0.7, min_years
    return max(0.0, 0.7 - 0.35 * (deficit - 1)), min_years


def _cosine(a: dict[str, int], b: dict[str, int]) -> float:
    if not a or not b:
        return 0.0
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    dot = sum(count * big.get(token, 0) for token, count in small.items())
    if not dot:
        return 0.0
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


def _affinity_component(job: Job, profile: ResumeProfile) -> float:
    text = f"{job.title} {job.company or ''} {job.description or ''}"
    return _cosine(tokenize(text), profile.tokens)


def _build_reasons(
    scored: ScoreBreakdown,
    job_tier: Optional[str],
    min_years: Optional[float],
    profile: ResumeProfile,
) -> list[str]:
    reasons: list[str] = []
    if scored.matched_skills:
        shown = ", ".join(scored.matched_skills[:5])
        more = len(scored.matched_skills) - min(5, len(scored.matched_skills))
        suffix = f" +{more} more" if more > 0 else ""
        reasons.append(f"Skills match: {shown}{suffix}")
    if scored.matched_preferred_skills:
        reasons.append(
            f"Also has their nice-to-haves: {', '.join(scored.matched_preferred_skills[:3])}"
        )
    if job_tier and profile.seniority and job_tier == profile.seniority:
        reasons.append(f"Seniority aligns ({job_tier})")
    if min_years is not None and profile.years_experience is not None:
        if profile.years_experience >= min_years:
            reasons.append(f"Meets the {min_years:g}+ yrs experience bar")
    if scored.title >= 0.7 and profile.titles:
        reasons.append(f"Title is close to your {profile.titles[0]} background")
    if not reasons:
        reasons.append("Limited overlap with this resume — broadening your skills may help")
    return reasons[:5]


def score_job(job: Job, profile: ResumeProfile) -> ScoredJob:
    skills_score, matched_req, missing_req, matched_pref = _skills_component(job, profile)
    title_score = _title_component(job.title, profile)
    seniority_score, job_tier = _seniority_component(job, profile)
    experience_score, min_years = _experience_component(job, profile)
    affinity_score = _affinity_component(job, profile)

    breakdown = ScoreBreakdown(
        skills=round(skills_score, 3),
        title=round(title_score, 3),
        seniority=round(seniority_score, 3),
        experience=round(experience_score, 3),
        affinity=round(affinity_score, 3),
        matched_skills=matched_req + matched_pref,
        missing_required_skills=missing_req,
        matched_preferred_skills=matched_pref,
    )
    breakdown.reasons = _build_reasons(breakdown, job_tier, min_years, profile)

    total = (
        WEIGHTS["skills"] * skills_score
        + WEIGHTS["title"] * title_score
        + WEIGHTS["seniority"] * seniority_score
        + WEIGHTS["experience"] * experience_score
        + WEIGHTS["affinity"] * affinity_score
    )
    return ScoredJob(**job.model_dump(), score=round(max(0.0, min(1.0, total)) * 100, 1), breakdown=breakdown)
