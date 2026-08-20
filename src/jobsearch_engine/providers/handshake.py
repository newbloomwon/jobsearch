"""Handshake — university career-platform integration (best effort).

Handshake has no public jobs API: postings live behind institutional SSO.
The official path is their institution/partner API, which requires an
approval process (see https://support.joinhandshake.com — "EDU API").

For hackathon/demo purposes this adapter authenticates with a session cookie
copied from *your own* logged-in Handshake account (HANDSHAKE_SCHOOL +
HANDSHAKE_COOKIE) and parses the classic postings page HTML with the stdlib
parser — no extra dependencies. When Handshake changes their markup or the
session expires, the provider fails loudly-but-gracefully and the rest of
the search continues.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import quote_plus

import httpx

from ..models import Job, JobQuery
from .base import JobProvider, ProviderError

_JOB_HREF = re.compile(r"^/(?:stu/)?jobs/(\d+)")


class _JobLinkParser(HTMLParser):
    """Collect anchor text + hrefs for job posting links."""

    def __init__(self) -> None:
        super().__init__()
        self.jobs: dict[str, str] = {}  # job id -> anchor text
        self._href: Optional[str] = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        if _JOB_HREF.match(href):
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            match = _JOB_HREF.match(self._href)
            title = " ".join("".join(self._text).split())
            if match and title:
                self.jobs.setdefault(match.group(1), title)
            self._href = None
            self._text = []


class HandshakeProvider(JobProvider):
    name = "handshake"
    display_name = "Handshake"

    def __init__(
        self,
        school: Optional[str] = None,
        cookie: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.school = (school or "").strip().removeprefix("https://").split(".")[0]
        self.cookie = (cookie or "").strip()
        self.client = client

    def is_configured(self) -> bool:
        return bool(self.school and self.cookie)

    def not_configured_reason(self) -> str:
        return (
            "Handshake requires a logged-in session: set HANDSHAKE_SCHOOL (e.g. 'usf') "
            "and HANDSHAKE_COOKIE (Cookie header from your browser). "
            "For production, apply for Handshake's official partner API."
        )

    async def search(self, query: JobQuery) -> list[Job]:
        base = f"https://{self.school}.joinhandshake.com"
        url = f"{base}/postings?query={quote_plus(query.keywords)}&page=1"
        headers = {
            "Cookie": self.cookie,
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
            "Accept": "text/html",
        }
        client = self.client or httpx.AsyncClient(timeout=20, follow_redirects=True)
        try:
            try:
                resp = await client.get(url, headers=headers)
            except httpx.HTTPError as exc:
                raise ProviderError(f"Handshake request failed: {exc}") from exc
        finally:
            if self.client is None:
                await client.aclose()

        if "login" in str(resp.url):
            raise ProviderError(
                "Handshake session expired — re-copy the Cookie header into HANDSHAKE_COOKIE"
            )
        if resp.status_code in (401, 403):
            raise ProviderError("Handshake rejected the session cookie (403)")
        if resp.status_code != 200:
            raise ProviderError(f"Handshake returned HTTP {resp.status_code}")

        parser = _JobLinkParser()
        try:
            parser.feed(resp.text)
        except Exception as exc:
            raise ProviderError(f"Could not parse Handshake response: {exc}") from exc

        if not parser.jobs:
            raise ProviderError(
                "Handshake returned no parsable postings (markup may have changed, "
                "or the search had no results)"
            )

        return [
            Job(
                id=f"handshake:{job_id}",
                source=self.name,
                source_display=self.display_name,
                title=title,
                url=f"{base}/jobs/{job_id}",
                extra={"school": self.school},
            )
            for job_id, title in list(parser.jobs.items())[: query.results_wanted]
        ]
