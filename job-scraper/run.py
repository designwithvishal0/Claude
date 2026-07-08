#!/usr/bin/env python3
"""Daily job digest: pull fresh (<=24h old) postings from every configured
source, dedupe, and write a JSON + Markdown digest into data/.

Usage:
    python run.py [--config config.yaml] [--out-dir data]
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

from scraper.models import is_fresh, matches_keywords
from scraper.sources import adzuna, arbeitnow, jooble, remoteok, remotive

SOURCE_MODULES = {
    "remoteok": remoteok,
    "remotive": remotive,
    "arbeitnow": arbeitnow,
    "adzuna": adzuna,
    "jooble": jooble,
}

KEY_GATED = {"adzuna", "jooble"}


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run(config: dict) -> tuple:
    session = requests.Session()
    all_jobs = []
    errors = []
    skipped = []

    for name, enabled in (config.get("sources") or {}).items():
        module = SOURCE_MODULES.get(name)
        if module is None or not enabled:
            continue
        if name in KEY_GATED and not module.is_configured():
            skipped.append(f"{name} (no API key configured)")
            continue
        try:
            jobs = module.fetch(session, config)
            all_jobs.extend(jobs)
        except Exception as exc:  # one bad source shouldn't kill the run
            errors.append(f"{name}: {exc}")

    keywords = config.get("keywords") or []
    max_age_hours = config.get("max_age_hours", 24)
    now = datetime.now(timezone.utc)

    fresh = [j for j in all_jobs if is_fresh(j, max_age_hours, now)]
    matched = [
        j for j in fresh if matches_keywords(f"{j.title} {' '.join(j.tags)}", keywords)
    ]

    deduped = {}
    for j in matched:
        deduped.setdefault(j.dedupe_key(), j)
    result = sorted(
        deduped.values(),
        key=lambda j: j.posted_at or now,
        reverse=True,
    )

    return result, errors, skipped


def write_outputs(jobs: list, errors: list, skipped: list, out_dir: Path, now: datetime):
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = now.strftime("%Y-%m-%d")

    import json

    payload = {
        "generated_at": now.isoformat(),
        "job_count": len(jobs),
        "errors": errors,
        "skipped_sources": skipped,
        "jobs": [j.to_dict() for j in jobs],
    }
    json_path = out_dir / f"{date_str}.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (out_dir / "latest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [f"# Job digest — {date_str}", "", f"{len(jobs)} fresh postings (last 24h)."]
    if skipped:
        lines.append("")
        lines.append("_Skipped sources: " + ", ".join(skipped) + "_")
    if errors:
        lines.append("")
        lines.append("_Source errors: " + "; ".join(errors) + "_")
    lines.append("")

    by_source = {}
    for j in jobs:
        by_source.setdefault(j.source, []).append(j)

    for source, source_jobs in sorted(by_source.items()):
        lines.append(f"## {source} ({len(source_jobs)})")
        lines.append("")
        for j in source_jobs:
            posted = j.posted_at.strftime("%Y-%m-%d %H:%M UTC") if j.posted_at else "unknown"
            loc = f" — {j.location}" if j.location else ""
            lines.append(f"- [{j.title}]({j.url}) at **{j.company}**{loc} _(posted {posted})_")
        lines.append("")

    md_path = out_dir / f"{date_str}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    (out_dir / "latest.md").write_text("\n".join(lines), encoding="utf-8")

    return json_path, md_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(Path(__file__).parent / "config.yaml"))
    parser.add_argument("--out-dir", default=str(Path(__file__).parent / "data"))
    args = parser.parse_args()

    config = load_config(Path(args.config))
    jobs, errors, skipped = run(config)
    now = datetime.now(timezone.utc)
    json_path, md_path = write_outputs(jobs, errors, skipped, Path(args.out_dir), now)

    print(f"Wrote {len(jobs)} fresh postings to {json_path} and {md_path}")
    if skipped:
        print("Skipped:", ", ".join(skipped))
    if errors:
        print("Errors:", "; ".join(errors), file=sys.stderr)


if __name__ == "__main__":
    main()
