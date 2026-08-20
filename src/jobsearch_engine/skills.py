"""Skill taxonomy + detection shared by resume parsing and job scoring.

Detection runs a single combined regex per category over the text (fast even
for 20KB job descriptions), then maps each matched alias back to a canonical
skill name. Short/risky aliases ("go", "r") get extra boundary guards so they
don't fire inside "go-to-market" or "R&D".
"""
from __future__ import annotations

import re
from functools import lru_cache

# canonical skill -> aliases (the canonical name is always matched too)
_TAXONOMY: dict[str, tuple[str, ...]] = {
    # languages
    "python": ("python3",),
    "javascript": ("java script",),
    "typescript": ("ts",),
    "java": (),
    "c++": ("c plus plus",),
    "c#": ("c sharp",),
    "go": ("golang",),
    "rust": (),
    "ruby": (),
    "php": (),
    "swift": (),
    "kotlin": (),
    "scala": (),
    "sql": ("structured query language",),
    "bash": ("shell scripting", "shell script", "zsh"),
    "r": ("r language",),
    "matlab": (),
    "html": ("html5",),
    "css": ("css3",),
    "dart": (),
    "objective-c": ("objective c",),
    # frontend
    "react": ("react.js", "reactjs"),
    "next.js": ("nextjs",),
    "vue": ("vue.js", "vuejs"),
    "angular": ("angularjs",),
    "svelte": (),
    "redux": (),
    "tailwind css": ("tailwind", "tailwindcss"),
    "bootstrap": (),
    "sass": ("scss",),
    "webpack": (),
    "vite": (),
    "jest": (),
    "cypress": (),
    "playwright": (),
    "storybook": (),
    "d3.js": ("d3", "d3js"),
    # backend / frameworks
    "node.js": ("node", "nodejs"),
    "express": ("express.js", "expressjs"),
    "django": (),
    "flask": (),
    "fastapi": ("fast api",),
    "spring": ("spring boot",),
    "rails": ("ruby on rails", "ror"),
    "laravel": (),
    ".net": ("dotnet", "asp.net", "asp net"),
    "graphql": ("graph ql",),
    "grpc": (),
    "rest api": ("rest", "restful", "rest apis", "restful apis"),
    "celery": (),
    "websockets": ("websocket",),
    # data / ml
    "pandas": (),
    "numpy": (),
    "scipy": (),
    "scikit-learn": ("sklearn", "scikit learn"),
    "pytorch": ("torch",),
    "tensorflow": (),
    "keras": (),
    "xgboost": (),
    "jupyter": ("jupyter notebooks", "jupyter notebook"),
    "spark": ("pyspark", "apache spark"),
    "hadoop": (),
    "hive": (),
    "airflow": ("apache airflow",),
    "dbt": (),
    "tableau": (),
    "power bi": ("powerbi", "power-bi"),
    "looker": (),
    "excel": (),
    "machine learning": (),
    "deep learning": (),
    "nlp": ("natural language processing",),
    "computer vision": (),
    "llm": ("llms", "large language model", "large language models"),
    "mlflow": (),
    "a/b testing": ("ab testing", "split testing", "a/b test"),
    "snowflake": (),
    "redshift": (),
    "bigquery": ("big query",),
    "databricks": (),
    # cloud / infra
    "aws": ("amazon web services", "ec2", "s3", "lambda", "aws lambda"),
    "gcp": ("google cloud", "google cloud platform"),
    "azure": ("microsoft azure",),
    "docker": (),
    "kubernetes": ("k8s",),
    "terraform": (),
    "jenkins": (),
    "github actions": (),
    "gitlab ci": (),
    "ci/cd": ("cicd", "continuous integration", "continuous delivery"),
    "linux": ("unix",),
    "nginx": (),
    "prometheus": (),
    "grafana": (),
    "datadog": (),
    "helm": (),
    "ansible": (),
    "serverless": (),
    "microservices": ("microservice",),
    # databases
    "postgresql": ("postgres",),
    "mysql": (),
    "mongodb": ("mongo",),
    "sqlite": (),
    "elasticsearch": ("elastic search",),
    "dynamodb": ("dynamo db",),
    "cassandra": (),
    "redis": (),
    "firebase": (),
    "sql server": ("mssql",),
    "oracle": (),
    # mobile
    "android": (),
    "ios": (),
    "react native": ("react-native",),
    "flutter": (),
    # practices / tools
    "git": ("github",),
    "selenium": (),
    "unit testing": ("unit tests", "unit test"),
    "tdd": ("test driven development", "test-driven development"),
    "agile": ("agile methodologies",),
    "scrum": (),
    "jira": (),
    "oauth": ("oauth2", "oauth 2"),
    "jwt": ("json web token", "json web tokens"),
    "cryptography": ("encryption",),
    "owasp": (),
    "penetration testing": ("pentesting", "pen testing"),
    "figma": (),
    "ux": ("user experience",),
}

# Words that mark a skill as preferred rather than required.
_PREFERRED_MARKERS = re.compile(
    r"\b(nice to have|preferred|prefer|plus|bonus|desirable|good to have|"
    r"not required|optional|familiarity with)\b",
    re.IGNORECASE,
)


def _alias_regex(alias: str) -> str:
    escaped = re.escape(alias)
    if len(alias) <= 3:
        # Guard short tokens against hyphen and ampersand neighbors too
        # ("go-to-market", "R&D") — the lookarounds block only [a-z0-9] by default.
        return rf"(?<![a-z0-9-&]){escaped}(?![a-z0-9-&])"
    return rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"


def _build_matcher():
    alias_to_canonical: dict[str, str] = {}
    patterns: list[str] = []
    for canonical, aliases in _TAXONOMY.items():
        for alias in (canonical, *aliases):
            low = alias.lower()
            if low not in alias_to_canonical:
                alias_to_canonical[low] = canonical
                patterns.append(_alias_regex(low))
    # Longest-first alternation so "github actions" wins over "git"/"github".
    patterns.sort(key=len, reverse=True)
    combined = re.compile("|".join(patterns), re.IGNORECASE)
    return combined, alias_to_canonical


_COMBINED, _ALIAS_TO_CANONICAL = _build_matcher()

ALL_SKILLS = sorted(_TAXONOMY.keys())


def find_skills(text: str) -> dict[str, int]:
    """Return {canonical_skill: occurrences} found in *text*."""
    if not text:
        return {}
    found: dict[str, int] = {}
    for m in _COMBINED.finditer(text):
        canonical = _ALIAS_TO_CANONICAL[m.group(0).lower()]
        found[canonical] = found.get(canonical, 0) + 1
    return found


@lru_cache(maxsize=2048)
def _chunks(text: str) -> tuple[str, ...]:
    """Split into bullet/sentence chunks, cached so scoring is cheap."""
    parts = re.split(r"[\n\r•·;]|(?<=[.!?])\s+", text)
    return tuple(p.strip() for p in parts if len(p.strip()) >= 3)


def detect_skills_detailed(text: str) -> tuple[dict[str, int], dict[str, int]]:
    """Classify detected skills as (required, preferred) using context.

    A skill counts as preferred when every chunk it appears in also contains
    a marker like "nice to have" / "plus" / "preferred".
    """
    required: dict[str, int] = {}
    preferred: dict[str, int] = {}
    for chunk in _chunks(text):
        chunk_preferred = bool(_PREFERRED_MARKERS.search(chunk))
        for skill, count in find_skills(chunk).items():
            target = preferred if chunk_preferred else required
            target[skill] = max(target.get(skill, 0), count)
    for skill in list(preferred):
        # A skill mentioned as required anywhere outranks its preferred mention.
        if skill in required:
            preferred.pop(skill)
    return required, preferred
