"""Provider interface implemented by every platform integration."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Job, JobQuery


class ProviderError(Exception):
    """A provider failed in an expected way (blocked, bad creds, parse)."""


class ProviderNotConfigured(ProviderError):
    """Raised when a provider lacks the env credentials it needs."""


class JobProvider(ABC):
    """One job platform integration.

    Implementations must never raise on `search` for environmental problems
    (missing credentials, upstream 403, timeouts) — the pipeline catches
    everything, but well-behaved providers return clean ProviderErrors with
    a message the frontend can show next to the provider chip.
    """

    name: str = "provider"
    display_name: str = "Provider"

    def is_configured(self) -> bool:
        """False when required env credentials are missing."""
        return True

    def not_configured_reason(self) -> str:
        return "Missing credentials — see the provider's docstring / README"

    @abstractmethod
    async def search(self, query: JobQuery) -> list[Job]:
        """Fetch normalized Jobs for the query. May raise ProviderError."""
        raise NotImplementedError
