"""Shared job record shape and helpers used by every source adapter."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Job:
    source: str
    title: str
    company: str
    url: str
    location: str = ""
    remote: Optional[bool] = None
    posted_at: Optional[datetime] = None  # timezone-aware UTC, None if unknown
    salary: str = ""
    tags: list = field(default_factory=list)

    def dedupe_key(self) -> str:
        if self.url:
            return self.url.strip().lower().rstrip("/")
        return f"{self.title.strip().lower()}::{self.company.strip().lower()}"

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "location": self.location,
            "remote": self.remote,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "salary": self.salary,
            "tags": self.tags,
        }


def is_fresh(job: Job, max_age_hours: int, now: Optional[datetime] = None) -> bool:
    """A job with no known posted_at is kept (can't prove it's stale) but
    flagged by the caller via job.posted_at is None if strict freshness matters."""
    if job.posted_at is None:
        return True
    now = now or datetime.now(timezone.utc)
    age = now - job.posted_at
    return 0 <= age.total_seconds() <= max_age_hours * 3600


def matches_keywords(text: str, keywords: list) -> bool:
    if not keywords:
        return True
    text_low = text.lower()
    return any(kw.lower() in text_low for kw in keywords)


def parse_epoch(value) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        v = value.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None
