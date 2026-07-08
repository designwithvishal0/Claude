"""Jooble — free job search API. Requires a free API key from
https://jooble.org/api/about (instant signup, no cost). Skipped
automatically if not configured.

Jooble is a licensed job meta-search engine: it aggregates listings from
employer career sites and other boards under its own data agreements. It is
not a scraper of any single named site (LinkedIn/Naukri/etc.) operated by us.
"""

import os

import requests

from ..models import Job, parse_iso

BASE_URL = "https://jooble.org/api/{key}"


def is_configured() -> bool:
    return bool(os.environ.get("JOOBLE_API_KEY"))


def fetch(session: requests.Session, config: dict) -> list:
    key = os.environ.get("JOOBLE_API_KEY")
    keywords = config.get("keywords") or []
    body = {
        "keywords": " ".join(keywords),
        "location": config.get("location", ""),
    }

    resp = session.post(BASE_URL.format(key=key), json=body, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for row in data.get("jobs", []):
        # Jooble's "updated" timestamp has no documented timezone; treated as UTC.
        jobs.append(
            Job(
                source="Jooble",
                title=(row.get("title") or "").strip(),
                company=(row.get("company") or "").strip(),
                url=row.get("link", ""),
                location=(row.get("location") or "").strip(),
                posted_at=parse_iso((row.get("updated") or "").replace(" ", "T")),
                salary=row.get("salary", "") or "",
                tags=[row.get("type")] if row.get("type") else [],
            )
        )
    return jobs
