from __future__ import annotations

import pytest

from jobsearch_engine import build_profile

SAMPLE_RESUME = """
Jane Doe
 jane.doe@example.com · (555) 010-3344 · New York, NY

EXPERIENCE

Software Engineer — Bright Apps LLC, New York, NY        2022 – Present
- Built customer-facing dashboards with React, TypeScript and Redux.
- Developed backend services in Python (FastAPI, Django) backed by PostgreSQL and Redis.
- Deployed with Docker and Kubernetes on AWS; set up CI/CD via GitHub Actions.
- Wrote unit tests with Jest and pytest coverage above 85%.

Junior Web Developer — PixelWorks Inc., Remote           2020 – 2022
- Maintained JavaScript and Node.js services; migrated legacy PHP pages.
- Used MySQL, Git and agile/scrum workflows daily.

SKILLS
Python, JavaScript, TypeScript, React, Node.js, SQL (PostgreSQL, MySQL),
AWS, Docker, Kubernetes, Git, REST APIs, GraphQL, HTML/CSS

EDUCATION
B.S. Computer Science, State University, 2020
"""


@pytest.fixture(scope="session")
def resume_profile():
    return build_profile(SAMPLE_RESUME)
