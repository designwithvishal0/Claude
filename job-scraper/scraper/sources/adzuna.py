"""Adzuna — free-tier job search API. Requires a free app_id/app_key from
https://developer.adzuna.com/. Skipped automatically if not configured.

Adzuna aggregates postings from thousands of company career pages and job
boards per country (set `adzuna_country`, e.g. "in" for India, "us", "gb").
It is a licensed aggregator, not a scraper of any single named site.
"""

import os

import requests

from ..models import Job, parse_iso

BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


def is_configured() -> bool:
    return bool(os.environ.get("ADZUNA_APP_ID") and os.environ.get("ADZUNA_APP_KEY"))


def fetch(session: requests.Session, config: dict) -> list:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    country = config.get("adzuna_country", "us")

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": 50,
        "sort_by": "date",
        "max_days_old": 1,
    }
    keywords = config.get("keywords") or []
    if keywords:
        params["what"] = " ".join(keywords)
    location = config.get("location")
    if location:
        params["where"] = location

    url = BASE_URL.format(country=country)
    resp = session.get(url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for row in data.get("results", []):
        company = (row.get("company") or {}).get("display_name", "")
        location_name = (row.get("location") or {}).get("display_name", "")
        salary_min, salary_max = row.get("salary_min"), row.get("salary_max")
        salary = f"{salary_min:.0f} - {salary_max:.0f}" if salary_min and salary_max else ""
        jobs.append(
            Job(
                source="Adzuna",
                title=row.get("title", "").strip(),
                company=company.strip(),
                url=row.get("redirect_url", ""),
                location=location_name,
                posted_at=parse_iso(row.get("created")),
                salary=salary,
                tags=[c.get("label") for c in [row.get("category") or {}] if c.get("label")],
            )
        )
    return jobs
