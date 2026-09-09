from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from ..models import JobPosting
from .base import USER_AGENT, JobSource

FEED_URLS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "https://weworkremotely.com/categories/remote-product-jobs.rss",
]


class WeWorkRemotelySource(JobSource):
    """We Work Remotely's public per-category RSS feeds. Free, no key required."""

    name = "weworkremotely"

    def fetch(self) -> list[JobPosting]:
        postings: list[JobPosting] = []
        for feed_url in FEED_URLS:
            postings.extend(self._fetch_feed(feed_url))
        return postings

    def _fetch_feed(self, feed_url: str) -> list[JobPosting]:
        resp = requests.get(feed_url, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        postings = []
        for item in root.findall("./channel/item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            region = (item.findtext("region") or "").strip()
            pub_date = item.findtext("pubDate")
            if not title or not link or not pub_date:
                continue
            try:
                posted_at = parsedate_to_datetime(pub_date)
                if posted_at.tzinfo is None:
                    posted_at = posted_at.replace(tzinfo=timezone.utc)
                else:
                    posted_at = posted_at.astimezone(timezone.utc)
            except (TypeError, ValueError):
                continue

            # WWR titles are "Company: Position"
            company, _, position = title.partition(":")
            postings.append(
                JobPosting(
                    source=self.name,
                    title=(position or title).strip(),
                    company=company.strip() if position else "",
                    url=link,
                    posted_at=posted_at,
                    location=region or "Remote",
                )
            )
        return postings
