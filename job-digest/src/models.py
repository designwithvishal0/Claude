from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class JobPosting:
    """A single normalized job posting from any source."""

    source: str
    title: str
    company: str
    url: str
    posted_at: datetime  # timezone-aware UTC
    location: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def dedup_key(self) -> str:
        return f"{self.company.strip().lower()}|{self.title.strip().lower()}"

    def age_hours(self, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        return (now - self.posted_at).total_seconds() / 3600

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "posted_at": self.posted_at.isoformat(),
            "location": self.location,
            "tags": self.tags,
        }
