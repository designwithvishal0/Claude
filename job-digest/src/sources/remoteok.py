from __future__ import annotations

from datetime import datetime, timezone

import requests

from ..models import JobPosting
from .base import USER_AGENT, JobSource

API_URL = "https://remoteok.com/api"


class RemoteOKSource(JobSource):
    """RemoteOK's public JSON API. Free, no key required.

    Their API terms ask that consumers credit "Remote OK" and link back to
    remoteok.com — both are done in the digest output.
    """

    name = "remoteok"

    def fetch(self) -> list[JobPosting]:
        resp = requests.get(API_URL, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
        rows = resp.json()

        postings = []
        for row in rows:
            # The first element is a legal/metadata blob, not a job.
            if not isinstance(row, dict) or "position" not in row:
                continue
            try:
                posted_at = datetime.fromisoformat(row["date"])
                if posted_at.tzinfo is None:
                    posted_at = posted_at.replace(tzinfo=timezone.utc)
            except (KeyError, ValueError):
                continue

            postings.append(
                JobPosting(
                    source=self.name,
                    title=row.get("position", "").strip(),
                    company=row.get("company", "").strip(),
                    url=row.get("url") or f"https://remoteok.com/remote-jobs/{row.get('id', '')}",
                    posted_at=posted_at,
                    location=row.get("location", "") or "Remote",
                    tags=row.get("tags", []) or [],
                )
            )
        return postings
