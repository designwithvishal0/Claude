"""RemoteOK — free public JSON API, no key required.
Docs: https://remoteok.com/api
"""

import requests

from ..models import Job, parse_epoch

API_URL = "https://remoteok.com/api"


def fetch(session: requests.Session, config: dict) -> list:
    headers = {"User-Agent": "daily-job-digest/1.0 (personal use; see README)"}
    resp = session.get(API_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for row in data:
        # First element of the response is a metadata/legal blob, not a job.
        if not isinstance(row, dict) or "id" not in row:
            continue
        jobs.append(
            Job(
                source="RemoteOK",
                title=row.get("position", "").strip(),
                company=row.get("company", "").strip(),
                url=row.get("url") or row.get("apply_url", ""),
                location=row.get("location", "").strip(),
                remote=True,
                posted_at=parse_epoch(row.get("epoch")),
                salary=_salary(row),
                tags=row.get("tags", []) or [],
            )
        )
    return jobs


def _salary(row: dict) -> str:
    lo, hi = row.get("salary_min"), row.get("salary_max")
    if lo and hi:
        return f"${lo:,} - ${hi:,}"
    return ""
