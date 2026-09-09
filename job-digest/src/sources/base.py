from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import JobPosting

USER_AGENT = "job-digest-bot/1.0 (personal job search aggregator; contact: designwithvishal0@gmail.com)"


class JobSource(ABC):
    """A pluggable job source. Implementations must only use each
    platform's public, documented, ToS-compliant access method (a JSON/RSS
    API, not HTML scraping of a logged-in or bot-protected surface)."""

    name: str

    @abstractmethod
    def fetch(self) -> list[JobPosting]:
        """Return all postings currently visible from this source.
        Freshness filtering happens later in the aggregator."""
        raise NotImplementedError


class UnavailableSource(JobSource):
    """Placeholder for a platform we deliberately do not scrape.

    Used for LinkedIn, Naukri, and X/Twitter: none offer a free public API
    for job search, and fetching their job listings outside an official
    partner API means impersonating a browser to route around ToS and
    active anti-bot defenses. That's not something this tool does. See
    job-digest/README.md for the legitimate paths (official partner APIs,
    RSS where the platform offers one, or manual saved-search alerts).
    """

    def __init__(self, name: str, reason: str):
        self.name = name
        self.reason = reason

    def fetch(self) -> list[JobPosting]:
        return []
