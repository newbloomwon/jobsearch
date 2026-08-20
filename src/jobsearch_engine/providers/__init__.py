"""Provider registry built from environment settings."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from .adzuna import AdzunaProvider
from .base import JobProvider, ProviderError, ProviderNotConfigured
from .handshake import HandshakeProvider
from .jobspy_provider import JobSpyProvider
from .jooble import JoobleProvider
from .sample import SampleProvider

__all__ = [
    "JobProvider",
    "ProviderError",
    "ProviderNotConfigured",
    "Settings",
    "build_registry",
]


@dataclass
class Settings:
    """Env-backed configuration for provider construction."""

    adzuna_app_id: Optional[str] = None
    adzuna_app_key: Optional[str] = None
    jooble_api_key: Optional[str] = None
    handshake_school: Optional[str] = None
    handshake_cookie: Optional[str] = None
    jobspy_enabled: bool = True
    jobspy_proxies: list[str] = field(default_factory=list)
    include_sample: bool = False

    @classmethod
    def from_env(cls, env: Optional[dict[str, str]] = None) -> "Settings":
        env = env if env is not None else dict(os.environ)
        proxies_raw = env.get("JOBSPY_PROXIES", "").strip()
        return cls(
            adzuna_app_id=env.get("ADZUNA_APP_ID") or None,
            adzuna_app_key=env.get("ADZUNA_APP_KEY") or None,
            jooble_api_key=env.get("JOOBLE_API_KEY") or None,
            handshake_school=env.get("HANDSHAKE_SCHOOL") or None,
            handshake_cookie=env.get("HANDSHAKE_COOKIE") or None,
            jobspy_enabled=env.get("JOBSPY_ENABLED", "1").strip().lower()
            not in {"0", "false", "no", "off"},
            jobspy_proxies=[p for p in proxies_raw.split(",") if p.strip()],
            include_sample=env.get("JOBSEARCH_SAMPLE", "0").strip().lower()
            in {"1", "true", "yes", "on"},
        )


def build_registry(settings: Optional[Settings] = None) -> dict[str, JobProvider]:
    """Instantiate every provider. Unconfigured ones stay in the registry so
    the API can surface them (with setup hints) to the frontend."""
    settings = settings or Settings.from_env()

    registry: dict[str, JobProvider] = {}
    if settings.jobspy_enabled:
        for site in ("linkedin", "indeed", "glassdoor", "zip_recruiter"):
            registry[site] = JobSpyProvider(site, proxies=settings.jobspy_proxies or None)
    registry["handshake"] = HandshakeProvider(
        school=settings.handshake_school, cookie=settings.handshake_cookie
    )
    registry["adzuna"] = AdzunaProvider(
        app_id=settings.adzuna_app_id, app_key=settings.adzuna_app_key
    )
    registry["jooble"] = JoobleProvider(api_key=settings.jooble_api_key)
    # "sample" is selectable on demand even when not in the default set.
    registry["sample"] = SampleProvider()
    return registry


def default_provider_names(settings: Settings) -> list[str]:
    """Providers used when the caller doesn't pick explicitly."""
    return [
        name
        for name, provider in build_registry(settings).items()
        if provider.is_configured() and (name != "sample" or settings.include_sample)
    ]
