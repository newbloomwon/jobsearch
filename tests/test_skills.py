from jobsearch_engine.skills import detect_skills_detailed, find_skills


def test_finds_basic_skills():
    text = "Requirements: 3+ years of Python and React. Nice to have: Kubernetes."
    skills = find_skills(text)
    assert {"python", "react", "kubernetes"} <= set(skills)


def test_aliases_map_to_canonical():
    skills = find_skills("Experience with Postgres, k8s, Golang, sklearn and PyTorch.")
    assert {"postgresql", "kubernetes", "go", "scikit-learn", "pytorch"} <= set(skills)


def test_short_alias_guards():
    # "go-to-market" and "R&D" must not count as the Go / R skills.
    skills = find_skills("Own the go-to-market strategy. Researched R&D partnerships.")
    assert "go" not in skills
    assert "r" not in skills
    # Standalone mentions do count.
    assert "go" in find_skills("Services written in Go and Python.")


def test_c_plus_plus_and_ci_cd():
    skills = find_skills("Strong C++ background; CI/CD experience with Jenkins pipelines.")
    assert "c++" in skills
    assert "ci/cd" in skills
    assert "jenkins" in skills


def test_dedupes_duplicate_mentions():
    skills = find_skills("Python here. Python there. PYTHON everywhere.")
    assert skills["python"] == 3


def test_required_vs_preferred_classification():
    text = (
        "You need Python and React.\n"
        "Nice to have: Kubernetes and Spark.\n"
        "We prefer familiarity with GraphQL."
    )
    required, preferred = detect_skills_detailed(text)
    assert "python" in required and "react" in required
    assert "kubernetes" in preferred and "spark" in preferred
    assert "graphql" in preferred


def test_required_outranks_preferred():
    text = "Requirements: Docker. Nice to have: Docker."
    required, preferred = detect_skills_detailed(text)
    assert "docker" in required
    assert "docker" not in preferred


def test_empty_text():
    assert find_skills("") == {}
    assert detect_skills_detailed("   ") == ({}, {})
