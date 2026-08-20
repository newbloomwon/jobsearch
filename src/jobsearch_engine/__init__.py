"""jobsearch engine — framework-agnostic job aggregation + resume matching.

Embed directly (Python) or drive it through the thin HTTP layer in
`jobsearch_api`. Nothing in this package imports a web framework.
"""
from .dedupe import dedupe_jobs
from .models import (
    Job,
    JobQuery,
    ProviderResult,
    ResumeProfile,
    ScoreBreakdown,
    ScoredJob,
    SearchResponse,
)
from .pipeline import search
from .providers import (
    ProviderError,
    Settings,
    build_registry,
    default_provider_names,
)
from .resume import ResumeParseError, build_profile, extract_text
from .scoring import analyze_job, score_job
from .skills import find_skills

__version__ = "0.1.0"

__all__ = [
    "Job",
    "JobQuery",
    "ProviderError",
    "ProviderResult",
    "ResumeParseError",
    "ResumeProfile",
    "ScoreBreakdown",
    "ScoredJob",
    "SearchResponse",
    "Settings",
    "analyze_job",
    "build_profile",
    "build_registry",
    "default_provider_names",
    "dedupe_jobs",
    "extract_text",
    "find_skills",
    "score_job",
    "search",
]
