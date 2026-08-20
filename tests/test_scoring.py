from datetime import date

from jobsearch_engine import Job, ResumeProfile
from jobsearch_engine.scoring import analyze_job, score_job


def _job(title="Software Engineer", description="", **overrides) -> Job:
    return Job(
        id="t:1",
        source="sample",
        title=title,
        company="Testco",
        posted_at=date(2026, 8, 15),
        description=description,
        **overrides,
    )


def _profile(**overrides) -> ResumeProfile:
    defaults = dict(
        skills=["python", "react", "typescript", "postgresql", "docker"],
        titles=["Software Engineer"],
        seniority="mid",
        years_experience=5,
        tokens={"python": 3, "react": 2, "engineer": 2, "api": 1},
    )
    defaults.update(overrides)
    return ResumeProfile(**defaults)


STRONG_DESC = (
    "Requirements: 4+ years with Python and React. TypeScript and PostgreSQL required. "
    "Docker in production. You will build APIs for our platform team."
)
WEAK_DESC = (
    "Requirements: 8+ years of Java and Spring. Deep Android experience required. "
    "Kotlin, Cassandra and Flutter experience needed for our mobile team."
)


def test_strong_match_scores_higher_than_weak():
    profile = _profile()
    strong = score_job(analyze_job(_job(description=STRONG_DESC)), profile)
    weak = score_job(analyze_job(_job(description=WEAK_DESC)), profile)
    assert strong.score > weak.score
    assert strong.score >= 60
    assert weak.score <= strong.score - 15


def test_breakdown_lists_matched_and_missing():
    profile = _profile()
    scored = score_job(analyze_job(_job(description=STRONG_DESC)), profile)
    bd = scored.breakdown
    assert "python" in bd.matched_skills
    assert "docker" in bd.matched_skills
    assert bd.missing_required_skills == []
    assert bd.reasons, "expected human-readable reasons"
    assert all(0.0 <= getattr(bd, k) <= 1.0 for k in ("skills", "title", "seniority", "experience", "affinity"))


def test_missing_required_skills_penalized_and_reported():
    profile = _profile()
    scored = score_job(analyze_job(_job(description=WEAK_DESC)), profile)
    assert "java" in scored.breakdown.missing_required_skills
    assert scored.breakdown.skills < 0.4


def test_no_skills_in_job_is_neutral_not_zero():
    scored = score_job(analyze_job(_job(description="Come join our fast-moving team!")), _profile())
    assert scored.breakdown.skills == 0.5
    assert 0 <= scored.score <= 100


def test_seniority_mismatch_lowers_score():
    profile = _profile(seniority="junior", years_experience=1)
    mid = score_job(analyze_job(_job(title="Software Engineer")), profile)
    principal = score_job(analyze_job(_job(title="Principal Software Engineer")), profile)
    assert mid.breakdown.seniority > principal.breakdown.seniority


def test_experience_component_meets_bar():
    profile = _profile(years_experience=6)
    meets = score_job(analyze_job(_job(description="Requirements: 5+ years experience.")), profile)
    short = score_job(analyze_job(_job(description="Requirements: 10+ years experience.")), profile)
    assert meets.breakdown.experience == 1.0
    assert short.breakdown.experience < 0.5


def test_score_range_clamped():
    profile = _profile(
        skills=["python"],
        titles=["Software Engineer"],
        seniority="senior",
        years_experience=20,
        tokens={},
    )
    job = _job(
        title="Senior Python Software Engineer",
        description="Python required. 3+ years. Python python python.",
    )
    scored = score_job(analyze_job(job), profile)
    assert 0.0 <= scored.score <= 100.0


def test_preferred_only_job_no_duplicate_matches():
    # A job listing only nice-to-haves must not double-count those skills
    # via the "no required skills" fallback.
    job = analyze_job(_job(description="Nice to have: Python and React. Join our team!"))
    profile = _profile(skills=["python"])
    scored = score_job(job, profile)
    assert sorted(scored.breakdown.matched_skills) == ["python"]
    assert scored.breakdown.matched_preferred_skills == ["python"]
    # Matched 1 of the 2 nice-to-haves: weight 1*1 / (2*0 + 1*2) = 0.5
    assert scored.breakdown.skills == 0.5


def test_preferred_skills_boost():
    base = _profile(skills=["python"])
    no_pref = score_job(analyze_job(_job(description="Requirements: Python.")), base)
    with_pref = score_job(
        analyze_job(_job(description="Requirements: Python. Nice to have: Rust.")), base
    )
    # Missing a preferred skill shouldn't beat having none listed, but both
    # should outrank missing the required skill entirely.
    assert no_pref.breakdown.skills == 1.0
    assert abs(with_pref.breakdown.skills - 2 / 3) < 0.002
    assert with_pref.breakdown.matched_preferred_skills == []
