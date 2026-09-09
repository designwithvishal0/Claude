from __future__ import annotations

import re
from datetime import datetime, timezone

import requests

from ..models import JobPosting
from .base import USER_AGENT, JobSource

SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
ITEM_URL = "https://hn.algolia.com/api/v1/items/{id}"

# Matches a comment's first line, formatted by convention as
# "Company | Role | Location | ..."-ish free text. We only need a title.
_TAG_RE = re.compile(r"<[^>]+>")


class HNWhoIsHiringSource(JobSource):
    """Hacker News's monthly "Who is hiring?" thread, via the public,
    keyless HN Algolia API. Each top-level comment is one job posting."""

    name = "hn_hiring"

    def fetch(self) -> list[JobPosting]:
        thread_id = self._latest_thread_id()
        if not thread_id:
            return []

        resp = requests.get(ITEM_URL.format(id=thread_id), headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
        thread = resp.json()

        postings = []
        for comment in thread.get("children", []) or []:
            text = comment.get("text") or ""
            if not text or comment.get("author") is None:
                continue
            created_at = comment.get("created_at")
            if not created_at:
                continue
            try:
                posted_at = datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(timezone.utc)
            except ValueError:
                continue

            title = self._first_line(text)
            if not title:
                continue

            postings.append(
                JobPosting(
                    source=self.name,
                    title=title[:200],
                    company=comment.get("author", ""),
                    url=f"https://news.ycombinator.com/item?id={comment.get('id')}",
                    posted_at=posted_at,
                    location="",
                )
            )
        return postings

    def _latest_thread_id(self) -> str | None:
        resp = requests.get(
            SEARCH_URL,
            params={"tags": "story", "query": "Who is hiring"},
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
        for hit in resp.json().get("hits", []):
            title = hit.get("title", "")
            if title.startswith("Ask HN: Who is hiring?"):
                return hit.get("objectID")
        return None

    @staticmethod
    def _first_line(html_text: str) -> str:
        # Comments are HTML; the first <p> boundary marks the end of the
        # "Company | Role | Location" header line by convention.
        head = html_text.split("<p>", 1)[0]
        plain = _TAG_RE.sub(" ", head).replace("&#x2F;", "/").replace("&amp;", "&")
        return " ".join(plain.split())
