import pytest

from jobsearch_engine.resume import extract_text
from jobsearch_engine.resume.profile import (
    build_profile,
    detect_seniority,
    detect_titles,
    detect_years,
)


def test_skills_extracted(resume_profile):
    assert {"python", "react", "typescript", "postgresql", "aws", "docker"} <= set(
        resume_profile.skills
    )


def test_titles_extracted(resume_profile):
    titles_lower = [t.lower() for t in resume_profile.titles]
    assert any("software engineer" in t for t in titles_lower)
    assert any("web developer" in t for t in titles_lower)


def test_years_experience(resume_profile):
    # "85% coverage" won't match; no explicit "N years" -> None for this resume.
    assert detect_years("Over 5+ years of professional experience. Then 2 years more.") == 5


def test_seniority_detection():
    assert detect_seniority("Senior Software Engineer") == "senior"
    assert detect_seniority("Software Engineer Intern") == "intern"
    assert detect_seniority("Principal Architect") == "principal"
    assert detect_seniority("Director of Software Engineering") == "principal"
    assert detect_seniority("VP of Engineering") == "principal"
    assert detect_seniority("Junior Data Analyst") == "junior"
    assert detect_seniority("Software Engineer") is None


def test_profile_seniority_from_headline_when_titles_miss_it():
    profile = build_profile(
        "Director of Software Engineering\nSoftware Developer at ACME — Java and AWS."
    )
    assert profile.seniority == "principal"


def test_education_detected(resume_profile):
    assert resume_profile.education == "bachelor"


def test_profile_seniority_falls_back_to_years():
    profile = build_profile("Built things with Python for 6 years. Logistic coordinator.")
    assert profile.seniority == "senior"


def test_detect_titles_dedupes():
    titles = detect_titles("Data Scientist\ndata scientist\nML Engineer")
    assert len(titles) == 2


def test_extract_text_txt():
    text = extract_text("resume.txt", b"python developer")
    assert text == "python developer"


def test_extract_text_docx_roundtrip():
    import io

    import docx

    buffer = io.BytesIO()
    document = docx.Document()
    document.add_paragraph("Python developer with React experience")
    document.save(buffer)
    text = extract_text("resume.docx", buffer.getvalue())
    assert "Python developer" in text


def test_extract_text_rejects_empty():
    with pytest.raises(Exception):
        extract_text("resume.txt", b"   ")
