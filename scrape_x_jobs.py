#!/usr/bin/env python3
"""
X Job Scraper
Requires: pip install tweepy pandas rich python-dotenv

Usage:
  export X_BEARER_TOKEN="your_bearer_token_here"
  python scrape_x_jobs.py --queries queries.txt --output jobs.csv
"""

import os
import re
import csv
import argparse
from datetime import datetime, timezone, timedelta

import tweepy
from rich.console import Console
from rich.progress import track
from rich.table import Table

console = Console()

CATEGORY_KEYWORDS = {
    "eng": [
        "engineer", "developer", "frontend", "backend", "fullstack",
        "devops", "sre", "ios", "android", "mobile", "platform",
        "infrastructure", "data", "ml", "ai", "research",
    ],
    "design": [
        "designer", "ux", "ui", "product design", "visual design",
        "interaction", "figma", "creative",
    ],
    "pm": [
        "product manager", "program manager", "chief of staff",
        "strategy", "roadmap",
    ],
    "mktg": [
        "marketing", "growth", "seo", "content", "devrel",
        "developer advocate", "community", "social media",
    ],
}

SALARY_RE = re.compile(
    r"\$?(?P<lo>\d{2,3})[kK]?\s*[-–—]\s*\$?(?P<hi>\d{2,3})[kK]"
)

DEFAULT_QUERIES = [
    '#hiring OR "we\'re hiring" lang:en',
    "#techjobs (frontend OR backend OR fullstack) -apply",
    '"looking for" (developer OR designer OR engineer) #remote',
    '"open role" OR "job opening" (React OR Python OR Go) min_faves:5',
]


def classify(text: str) -> str:
    t = text.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return cat
    return "other"


def extract_salary(text: str) -> str | None:
    m = SALARY_RE.search(text)
    if not m:
        return None
    lo, hi = int(m.group("lo")), int(m.group("hi"))
    if lo < 20:
        return f"${lo}–${hi}/hr"
    return f"${lo}k–${hi}k"


def is_remote(text: str) -> bool:
    return bool(re.search(r"\bremote\b", text, re.I))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scrape job postings from X")
    p.add_argument(
        "--queries",
        default="-",
        help="File with one query per line, or - to use built-in defaults",
    )
    p.add_argument("--output", default="jobs.csv", help="Output CSV path")
    p.add_argument("--days", type=int, default=7, help="Look back N days (max 7 for free tier)")
    p.add_argument("--max", type=int, default=50, help="Max results per query (10–100)")
    p.add_argument("--no-preview", action="store_true", help="Skip the rich table preview")
    return p.parse_args()


def load_queries(path: str) -> list[str]:
    if path == "-":
        return DEFAULT_QUERIES
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def scrape_query(
    client: tweepy.Client,
    query: str,
    days: int,
    max_results: int,
) -> list[dict]:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    results = []

    try:
        resp = client.search_recent_tweets(
            query=query + " -is:retweet",
            start_time=start,
            max_results=max(10, min(max_results, 100)),
            tweet_fields=["created_at", "public_metrics", "author_id", "text"],
            user_fields=["username", "name", "verified", "public_metrics"],
            expansions=["author_id"],
        )
    except tweepy.TweepyException as exc:
        console.print(f"[red]Error for query '{query}': {exc}[/red]")
        return results

    if not resp.data:
        return results

    users = {u.id: u for u in (resp.includes.get("users") or [])}

    for tweet in resp.data:
        user = users.get(tweet.author_id)
        m = tweet.public_metrics or {}
        results.append(
            {
                "tweet_id": str(tweet.id),
                "tweet_url": (
                    f"https://x.com/{user.username}/status/{tweet.id}" if user else ""
                ),
                "handle": f"@{user.username}" if user else "",
                "name": user.name if user else "",
                "verified": getattr(user, "verified", False),
                "text": tweet.text,
                "category": classify(tweet.text),
                "remote": is_remote(tweet.text),
                "salary": extract_salary(tweet.text) or "",
                "likes": m.get("like_count", 0),
                "retweets": m.get("retweet_count", 0),
                "created_at": (
                    tweet.created_at.isoformat() if tweet.created_at else ""
                ),
                "query": query,
            }
        )

    return results


def preview_table(jobs: list[dict]) -> None:
    table = Table(title=f"X Job Postings ({len(jobs)} found)", show_lines=True)
    table.add_column("Handle", style="bold cyan", no_wrap=True)
    table.add_column("Category", style="magenta")
    table.add_column("Remote", justify="center")
    table.add_column("Salary")
    table.add_column("Likes", justify="right")
    table.add_column("Snippet")

    for j in jobs[:20]:
        table.add_row(
            j["handle"],
            j["category"],
            "✓" if j["remote"] else "",
            j["salary"] or "—",
            str(j["likes"]),
            j["text"][:80].replace("\n", " ") + "…",
        )

    console.print(table)
    if len(jobs) > 20:
        console.print(f"[dim]… and {len(jobs) - 20} more in the CSV.[/dim]")


def main() -> None:
    args = parse_args()

    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        console.print(
            "[bold red]Error:[/bold red] Set the X_BEARER_TOKEN environment variable.\n"
            "  Get one at https://developer.x.com/en/portal/dashboard"
        )
        raise SystemExit(1)

    client = tweepy.Client(bearer_token=token, wait_on_rate_limit=True)
    queries = load_queries(args.queries)

    console.print(f"[bold]Scraping {len(queries)} queries over the last {args.days} day(s)…[/bold]\n")

    all_jobs: list[dict] = []
    for q in track(queries, description="Querying X…"):
        batch = scrape_query(client, q, args.days, args.max)
        all_jobs.extend(batch)
        console.print(f"  [green]{len(batch):>3} tweets[/green] — {q[:70]}")

    # Deduplicate by tweet_id
    seen: set[str] = set()
    unique = []
    for j in all_jobs:
        if j["tweet_id"] not in seen:
            seen.add(j["tweet_id"])
            unique.append(j)

    console.print(
        f"\n[bold green]✓ {len(unique)} unique job tweets[/bold green] "
        f"({len(all_jobs) - len(unique)} duplicates removed)"
    )

    if not unique:
        console.print("[yellow]No results found. Try broadening your queries.[/yellow]")
        return

    if not args.no_preview:
        preview_table(unique)

    fields = [
        "tweet_id", "tweet_url", "handle", "name", "verified",
        "category", "remote", "salary", "likes", "retweets",
        "created_at", "text", "query",
    ]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(unique)

    console.print(f"\nSaved → [bold]{args.output}[/bold]")


if __name__ == "__main__":
    main()
