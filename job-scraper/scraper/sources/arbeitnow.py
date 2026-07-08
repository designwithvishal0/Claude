"""Arbeitnow — free public JSON API, no key required.
Docs: https://documenter.getpostman.com/view/12324248/TzsbEW9x
"""

import requests

from ..models import Job, parse_epoch

API_URL = "https://www.arbeitnow.com/api/job-board-api"


def fetch(session: requests.Session, config: dict) -> list:
    resp = session.get(API_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for row in data.get("data", []):
        jobs.append(
            Job(
                source="Arbeitnow",
                title=row.get("title", "").strip(),
                company=row.get("company_name", "").strip(),
                url=row.get("url", ""),
                location=row.get("location", "").strip(),
                remote=bool(row.get("remote")),
                posted_at=parse_epoch(row.get("created_at")),
                tags=(row.get("tags") or []) + (row.get("job_types") or []),
            )
        )
    return jobs
