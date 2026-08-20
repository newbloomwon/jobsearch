# JobSearch — resume-matched job aggregator

Aggregates job listings from **LinkedIn, Indeed, Glassdoor, ZipRecruiter, Adzuna,
Jooble and Handshake**, then scores every listing against an uploaded resume
(0–100, with a per-component breakdown explaining *why* it matched).

Built for a hackathon in two halves:

| Piece | Location | Owner |
|---|---|---|
| **Engine** — providers, dedupe, resume parsing, scoring | `src/jobsearch_engine/` | backend |
| **API** — thin FastAPI wrapper | `src/jobsearch_api/` | backend |
| **Frontend** — `index.html` at the repo root, served at `/` | repo root | frontend partner |

The engine is **framework-agnostic**: it's a pure-Python package with zero web
framework imports. Consume it via the HTTP API (any frontend framework works),
or embed it directly in any Python app.

---

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[api,resume,scrapers,dev]"
cp .env.example .env          # optional: fill in free API keys
uvicorn jobsearch_api.main:app --reload
```

Open <http://localhost:8000> — the frontend (`index.html` at the repo root) is
served at `/` and wired to the live API: upload a resume, pick platforms, and
Confirm runs a real scored search. The interactive API contract lives at
**`/docs`** (OpenAPI).

Zero-config behavior: with no API keys and no scrapers, everything still runs —
the offline `sample` provider returns deterministic jobs so the frontend can be
built before any key exists.

## How the frontend uses it (2 calls)

```bash
# 1. Upload a resume (PDF/DOCX/TXT) -> resumeId + parsed profile
curl -F "file=@resume.pdf" http://localhost:8000/api/resume

# 2. Search; jobs come back deduped + scored + ranked
curl -X POST http://localhost:8000/api/jobs/search -H 'Content-Type: application/json' -d '{
  "keywords": "software engineer",
  "location": "New York, NY",
  "providers": ["linkedin", "indeed", "glassdoor", "sample"],
  "resumeId": "<from step 1>"
}'
```

JSON responses use camelCase. Every job carries `score` (0–100) and a
`breakdown` object: five component scores, `matchedSkills`,
`missingRequiredSkills`, `matchedPreferredSkills`, and human-readable
`reasons[]` — ready to render directly.

<details>
<summary>Endpoint summary</summary>

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | Liveness + configured-provider counts |
| GET | `/api/providers` | Provider list with `configured` + setup hints |
| POST | `/api/resume` | Multipart file (or form `text`) → `resumeId` + profile |
| POST | `/api/resume/text` | JSON `{"text": "..."}` variant |
| POST | `/api/jobs/search` | Aggregate → dedupe → score → rank |

Search request fields: `keywords` (required), `location`, `country`,
`isRemote`, `jobType` (fulltime/parttime/contract/internship), `hoursOld`,
`resultsWanted` (per provider), `providers[]`, `resumeId` or `resumeText`,
`minScore`, `limit`. Scrape-backed providers can take 30–60s — the frontend
should allow for that (the `sample` provider is instant).

</details>

## Provider reality check

| Provider | Mechanism | Needs | Notes |
|---|---|---|---|
| `linkedin` | scraped via [JobSpy](https://github.com/speedyapply/JobSpy) | nothing (install `[scrapers]`) | Rate-limits around ~10 pages/IP; use proxies for volume |
| `indeed` | scraped via JobSpy | nothing | Most reliable scraper; `country` matters |
| `glassdoor` | scraped via JobSpy | nothing | **Flakiest board**: verified broken in jobspy 1.1.82 (Aug 2026) — returns 0 jobs; watch for lib updates |
| `zip_recruiter` | scraped via JobSpy | nothing | Bonus board, US/CA only |
| `adzuna` | official API | free key ([developer.adzuna.com](https://developer.adzuna.com)) | Reliable from datacenter IPs — recommended for demos |
| `jooble` | official API | free key ([jooble.org/api/about](https://jooble.org/api/about)) | Reliable; salary strings, shorter snippets |
| `handshake` | session-cookie adapter | your school login | See below |
| `sample` | offline fixture | nothing | Deterministic data for frontend dev |

**Handshake** has no public jobs API — postings sit behind university SSO
(their [EDU/partner API](https://support.joinhandshake.com/hc/en-us/articles/31061076506391-Getting-Started-with-EDU-API)
requires an approval process). For hackathon/demo use, log into *your own*
Handshake account in a browser, copy the `Cookie` request header, and set
`HANDSHAKE_SCHOOL` + `HANDSHAKE_COOKIE` in `.env`. The adapter fetches and
parses the postings page; if the session expires or markup changes it fails
gracefully and the rest of the search is unaffected.

**Scraping caveats (be honest at the demo):** scraped boards' ToS disallow
scraping; LinkedIn/Indeed actively block datacenter IPs, and results can be
empty or 403 from your deploy region. That's exactly why Adzuna/Jooble keys
and the `sample` provider exist — the deployed app degrades per-provider and
always returns a coherent response with per-provider status chips. For
heavier scraped volume, set `JOBSPY_PROXIES` (residential proxies).

## Architecture

```
┌─────────────────────── jobsearch_engine (pure Python) ───────────────────────┐
│                                                                              │
│  providers/                    resume/            scoring.py                 │
│  ├── jobspy_provider  (LI/In/GD/Zip)   parser.py  (pdf/docx/txt)   skills.py │
│  ├── adzuna, jooble   (official APIs)  profile.py (skills/years)  dedupe.py  │
│  ├── handshake        (session adapter)                                      │
│  └── sample           (offline fixtures)          pipeline.py                │
│                                                   fan-out → normalize →      │
│  models.py (Job/Query/ScoredJob/…)                dedupe → score → rank      │
└──────────────────────────────────────────────────────────────────────────────┘
                                  ▲
┌──────────────────── jobsearch_api (thin FastAPI layer) ──────────────────────┐
│  /api/resume  /api/jobs/search  /api/providers  /healthz  + frontend at /    │
└──────────────────────────────────────────────────────────────────────────────┘
```

Scoring = weighted blend: **skills overlap 50%** (required skills weighted 2×
nice-to-haves, detected from phrasing like "nice to have"/"plus"), **title
similarity 20%**, **seniority alignment 10%**, **years-of-experience fit 10%**,
**text affinity 10%** (cosine over token counts). Deterministic, no LLM calls,
fully unit-tested. Cross-board duplicates (same company+title, or same URL) are
merged and reported in `duplicatesRemoved`.

## Deployment

**Render (recommended, Docker):** repo already contains `render.yaml` —
create a new Web Service from the repo and it builds. Set `ADZUNA_APP_ID`,
`ADZUNA_APP_KEY`, `JOOBLE_API_KEY` in the dashboard (or any of `.env.example`'s
vars). Use at least the *Starter* plan (512 MB free instances are tight for
scraping).

**Any Docker host:**

```bash
docker build -t jobsearch .
docker run -p 8000:8000 --env-file .env jobsearch
```

**Railway/Fly:** point them at the Dockerfile; done.

Scaling notes: resumes are held in memory (24 h TTL) — fine for a single
instance; swap `jobsearch_api/store.py` for Redis when you outgrow that.

## Development

```bash
pip install -e ".[api,resume,scrapers,dev]"
pytest                                  # full suite, no network needed
pytest tests/test_scoring.py -q         # one file
```

- `scripts/smoke_jobspy.py` — live end-to-end check of the real scrapers
  (`python scripts/smoke_jobspy.py "python developer" "New York"`).
- CI (`.github/workflows/ci.yml`) runs the suite on push.
- Adding a provider: subclass `JobProvider` in
  `src/jobsearch_engine/providers/`, register it in `build_registry()` —
  everything downstream (dedupe, scoring, API) picks it up automatically.

## Credits

Scraping by [JobSpy](https://github.com/speedyapply/JobSpy) (MIT). Job data
from Adzuna & Jooble APIs.
