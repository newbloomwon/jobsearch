"""In-memory resume store with TTL.

Good enough for a single-instance hackathon deploy; swap for Redis/Postgres
if you scale out (the interface is two methods).
"""
from __future__ import annotations

import secrets
import time

from jobsearch_engine import ResumeProfile


class ResumeStore:
    def __init__(self, ttl_seconds: float = 24 * 3600):
        self.ttl = ttl_seconds
        self._entries: dict[str, tuple[ResumeProfile, float]] = {}

    def save(self, profile: ResumeProfile) -> str:
        self._prune()
        resume_id = secrets.token_urlsafe(12)
        self._entries[resume_id] = (profile, time.monotonic() + self.ttl)
        return resume_id

    def get(self, resume_id: str) -> ResumeProfile | None:
        self._prune()
        entry = self._entries.get(resume_id)
        if entry is None:
            return None
        return entry[0]

    def _prune(self) -> None:
        now = time.monotonic()
        expired = [key for key, (_, deadline) in self._entries.items() if deadline <= now]
        for key in expired:
            del self._entries[key]
