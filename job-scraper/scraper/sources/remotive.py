"""Remotive — free public JSON API, no key required.
Docs: https://remotive.com/api-documentation

Remotive's own terms ask API consumers not to hammer the endpoint (they
suggest at most ~4 calls/day and note results already lag live postings by
up to 24h). A once-a-day scheduled run stays comfortably within that.
"""

import requests

from ..models import Job, parse_iso

API_URL = "https://remotive.com/api/remote-jobs"


def fetch(session: requests.Session, config: dict) -> list:
    params = {}
    keywords = config.get("keywords") or []
    if keywords:
        params["search"] = keywords[0]

    resp = session.get(API_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for row in data.get("jobs", []):
        jobs.append(
            Job(
                source="Remotive",
                title=row.get("title", "").strip(),
                company=row.get("company_name", "").strip(),
                url=row.get("url", ""),
                location=row.get("candidate_required_location", "").strip(),
                remote=True,
                posted_at=parse_iso(row.get("publication_date")),
                salary=row.get("salary", "") or "",
                tags=row.get("tags", []) or [],
            )
        )
    return jobs
