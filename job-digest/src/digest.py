from __future__ import annotations

import json
from datetime import datetime, timezone

from .models import JobPosting

ATTRIBUTION = {
    "remoteok": "Source: Remote OK (remoteok.com)",
    "weworkremotely": "Source: We Work Remotely (weworkremotely.com)",
    "hn_hiring": "Source: Hacker News \"Who is hiring?\" (news.ycombinator.com)",
}


def to_json(postings: list[JobPosting], generated_at: datetime | None = None) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    payload = {
        "generated_at": generated_at.isoformat(),
        "count": len(postings),
        "postings": [p.to_dict() for p in postings],
    }
    return json.dumps(payload, indent=2)


def to_markdown(postings: list[JobPosting], generated_at: datetime | None = None) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    lines = [
        f"# Job digest — {generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"{len(postings)} posting(s) from the last 24 hours matching your config.",
        "",
    ]

    if not postings:
        lines.append("No fresh matches today.")
        return "\n".join(lines) + "\n"

    by_source: dict[str, list[JobPosting]] = {}
    for p in postings:
        by_source.setdefault(p.source, []).append(p)

    for source, items in by_source.items():
        lines.append(f"## {source} ({len(items)})")
        if source in ATTRIBUTION:
            lines.append(f"_{ATTRIBUTION[source]}_")
        lines.append("")
        for p in items:
            loc = f" — {p.location}" if p.location else ""
            lines.append(f"- [{p.title}]({p.url}) at **{p.company}**{loc} · {p.posted_at.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")

    return "\n".join(lines) + "\n"
