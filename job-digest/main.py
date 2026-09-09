#!/usr/bin/env python3
"""Daily job digest: collect postings from enabled sources, keep only
those from the last `freshness_hours`, and write a JSON + Markdown digest.

Usage:
    python3 main.py [--config config.yaml] [--out-dir digests]
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.aggregator import collect, filter_postings  # noqa: E402
from src.digest import to_json, to_markdown  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(Path(__file__).parent / "config.yaml"))
    parser.add_argument("--out-dir", default=str(Path(__file__).parent / "digests"))
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.config).read_text())

    now = datetime.now(timezone.utc)
    raw = collect(config.get("enabled_sources", []))
    fresh = filter_postings(
        raw,
        keywords=config.get("keywords", []),
        locations=config.get("locations", []),
        freshness_hours=config.get("freshness_hours", 24),
        now=now,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y-%m-%d")

    (out_dir / f"{stamp}.json").write_text(to_json(fresh, now))
    (out_dir / f"{stamp}.md").write_text(to_markdown(fresh, now))
    (out_dir / "latest.md").write_text(to_markdown(fresh, now))

    print(f"Collected {len(raw)} postings, {len(fresh)} fresh matches -> {out_dir}/{stamp}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
