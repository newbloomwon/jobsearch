"""Resume text → structured ResumeProfile (skills, titles, seniority, years)."""
from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from ..models import ResumeProfile
from ..skills import find_skills

_STOPWORDS = frozenset(
    """a an and are as at be by for from has have in into is it its of on or
    that the to was were will with you your our we they their this these those
    i my me worked work working using use used across over under within per
    etc via new including include includes team teams role roles year years
    experience experiences strong excellent great good ability able who whom
    while when where what how why all any each more most other some such no
    not than then there here also been being do does did doing have has had
    """.split()
)

_TITLE_RE = re.compile(
    r"\b([A-Za-z][A-Za-z/+& ]{2,40}?"
    r"(?:engineer|developer|scientist|analyst|manager|designer|architect|"
    r"consultant|administrator|specialist|programmer|intern|technician))\b",
    re.IGNORECASE,
)

_YEARS_RE = re.compile(r"\b(\d{1,2})(?:\s*[-–]\s*\d{1,2})?\s*\+?\s*years?\b", re.IGNORECASE)

_EDUCATION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("phd", re.compile(r"\b(ph\.?\s?d|doctorate)\b", re.IGNORECASE)),
    ("master", re.compile(r"\b(m\.?s\.?c?|master'?s?|mba)\b", re.IGNORECASE)),
    ("bachelor", re.compile(r"\b(b\.?s\.?c?|b\.?a\.?|bachelor)'?s?\b", re.IGNORECASE)),
    ("associate", re.compile(r"\bassociate'?s? degree\b", re.IGNORECASE)),
]

# seniority tier ladder index
SENIORITY_TIERS = ["intern", "junior", "mid", "senior", "staff", "principal"]
SENIORITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("intern", re.compile(r"\b(intern|internship)\b", re.IGNORECASE)),
    ("junior", re.compile(r"\b(junior|jr\.?|entry[- ]level|graduate)\b", re.IGNORECASE)),
    (
        "senior",
        re.compile(r"\b(senior|sr\.?|lead|head of|manager ii|experienced)\b", re.IGNORECASE),
    ),
    ("staff", re.compile(r"\b(staff)\b", re.IGNORECASE)),
    ("principal", re.compile(r"\b(principal|distinguished|architect)\b", re.IGNORECASE)),
]

TOKEN_RE = re.compile(r"[a-z][a-z+#./]{1,20}")


def tokenize(text: str) -> dict[str, int]:
    """Lowercased word counts, stopwords removed — input to cosine affinity."""
    counts = Counter(
        t for t in TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 2
    )
    return dict(counts)


def detect_seniority(text: str) -> Optional[str]:
    """Highest seniority tier mentioned in *text* (titles like 'Senior ...')."""
    highest: Optional[str] = None
    for tier, pattern in SENIORITY_PATTERNS:
        if pattern.search(text) and tier != "mid":
            if highest is None or SENIORITY_TIERS.index(tier) > SENIORITY_TIERS.index(highest):
                highest = tier
    return highest


def detect_years(text: str) -> Optional[float]:
    years: Optional[float] = None
    for match in _YEARS_RE.finditer(text):
        value = float(match.group(1))
        if value <= 45:  # sanity: ignore date ranges like "2016 - 2024 years"?
            years = value if years is None else max(years, value)
    return years


def detect_titles(text: str, limit: int = 4) -> list[str]:
    seen: list[str] = []
    for match in _TITLE_RE.finditer(text):
        title = " ".join(match.group(1).split()).title()
        if title.lower() not in {t.lower() for t in seen}:
            seen.append(title)
        if len(seen) >= limit:
            break
    return seen


def detect_education(text: str) -> Optional[str]:
    for level, pattern in _EDUCATION_PATTERNS:
        if pattern.search(text):
            return level
    return None


def build_profile(text: str) -> ResumeProfile:
    skills = sorted(find_skills(text).keys())
    titles = detect_titles(text)
    seniority = detect_seniority(" ".join(titles) if titles else text)
    # Fall back to years-based tier when no explicit seniority words appear.
    years = detect_years(text)
    if seniority is None and years is not None:
        seniority = "junior" if years < 2 else "mid" if years < 5 else "senior"
    return ResumeProfile(
        skills=skills,
        titles=titles,
        seniority=seniority,
        years_experience=years,
        education=detect_education(text),
        char_count=len(text),
        tokens=tokenize(text),
    )
