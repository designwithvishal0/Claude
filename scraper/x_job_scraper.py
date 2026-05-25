#!/usr/bin/env python3
"""
X (Twitter) Job Scraper
Searches X for job postings using the Twitter API v2.

Setup:
  pip install tweepy python-dotenv
  Set BEARER_TOKEN in .env or environment

Usage:
  python x_job_scraper.py
  python x_job_scraper.py --query "UX designer hiring" --max 100 --output jobs.csv
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import tweepy
except ImportError:
    sys.exit("Missing dependency: pip install tweepy python-dotenv")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # dotenv optional; rely on env vars


DEFAULT_QUERIES = [
    "#hiring #designer",
    "#hiring #uxdesigner",
    "#hiring #productdesigner",
    "#designjobs",
    "#UIUXjobs",
    "we're hiring designer",
    "looking for designer apply",
]

JOB_SIGNAL_WORDS = [
    "hiring", "apply", "job", "role", "position", "opportunity",
    "join our team", "remote", "full-time", "part-time", "contract",
    "salary", "compensation", "benefits", "opening",
]

EXCLUDE_TERMS = ["-is:retweet", "lang:en"]


def get_client(bearer_token: str) -> tweepy.Client:
    return tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)


def build_query(user_query: str) -> str:
    filters = " ".join(EXCLUDE_TERMS)
    return f"({user_query}) {filters}"


def is_job_post(text: str) -> bool:
    text_lower = text.lower()
    matches = sum(1 for w in JOB_SIGNAL_WORDS if w in text_lower)
    return matches >= 2


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://\S+", text)


def scrape_query(
    client: tweepy.Client,
    query: str,
    max_results: int,
) -> list[dict]:
    full_query = build_query(query)
    jobs: list[dict] = []
    fetched = 0
    per_page = min(max_results, 100)

    try:
        paginator = tweepy.Paginator(
            client.search_recent_tweets,
            query=full_query,
            tweet_fields=["created_at", "author_id", "text", "public_metrics"],
            user_fields=["name", "username"],
            expansions=["author_id"],
            max_results=per_page,
        )

        for response in paginator:
            if not response.data:
                break

            users_by_id: dict[int, tweepy.User] = {}
            if response.includes and "users" in response.includes:
                users_by_id = {u.id: u for u in response.includes["users"]}

            for tweet in response.data:
                if not is_job_post(tweet.text):
                    continue

                author = users_by_id.get(tweet.author_id)
                jobs.append(
                    {
                        "tweet_id": tweet.id,
                        "author_username": author.username if author else "",
                        "author_name": author.name if author else "",
                        "text": tweet.text.replace("\n", " "),
                        "posted_at": tweet.created_at.isoformat() if tweet.created_at else "",
                        "tweet_url": f"https://x.com/{author.username if author else 'i'}/status/{tweet.id}",
                        "urls": " | ".join(extract_urls(tweet.text)),
                        "likes": tweet.public_metrics.get("like_count", 0) if tweet.public_metrics else 0,
                        "retweets": tweet.public_metrics.get("retweet_count", 0) if tweet.public_metrics else 0,
                        "query": query,
                    }
                )
                fetched += 1
                if fetched >= max_results:
                    break

            if fetched >= max_results:
                break

    except tweepy.TweepyException as e:
        print(f"  API error for query '{query}': {e}", file=sys.stderr)

    return jobs


def deduplicate(jobs: list[dict]) -> list[dict]:
    seen: set[int] = set()
    unique: list[dict] = []
    for job in jobs:
        if job["tweet_id"] not in seen:
            seen.add(job["tweet_id"])
            unique.append(job)
    return unique


def save_csv(jobs: list[dict], path: str) -> None:
    if not jobs:
        print("No jobs to save.")
        return
    fieldnames = list(jobs[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(jobs)
    print(f"Saved {len(jobs)} jobs → {path}")


def save_json(jobs: list[dict], path: str) -> None:
    if not jobs:
        print("No jobs to save.")
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(jobs)} jobs → {path}")


def print_summary(jobs: list[dict]) -> None:
    print(f"\n{'='*60}")
    print(f"  Found {len(jobs)} job post(s) on X")
    print(f"{'='*60}")
    for i, job in enumerate(jobs[:5], 1):
        print(f"\n[{i}] @{job['author_username']} — {job['posted_at'][:10]}")
        print(f"    {job['text'][:120]}...")
        print(f"    {job['tweet_url']}")
    if len(jobs) > 5:
        print(f"\n  ... and {len(jobs) - 5} more.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape job postings from X")
    parser.add_argument(
        "--query",
        type=str,
        help="Custom search query (default: runs all built-in job queries)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=50,
        help="Max results per query (default: 50)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="x_jobs.csv",
        help="Output file path — .csv or .json (default: x_jobs.csv)",
    )
    parser.add_argument(
        "--token",
        type=str,
        help="Twitter Bearer Token (or set BEARER_TOKEN env var)",
    )
    args = parser.parse_args()

    bearer_token = args.token or os.getenv("BEARER_TOKEN")
    if not bearer_token:
        sys.exit(
            "Error: Twitter Bearer Token required.\n"
            "  Set BEARER_TOKEN=<token> in .env or pass --token <token>\n"
            "  Get one at https://developer.x.com/en/portal/dashboard"
        )

    client = get_client(bearer_token)
    queries = [args.query] if args.query else DEFAULT_QUERIES

    all_jobs: list[dict] = []
    for q in queries:
        print(f"Searching: {q}")
        results = scrape_query(client, q, args.max)
        print(f"  → {len(results)} job posts found")
        all_jobs.extend(results)

    all_jobs = deduplicate(all_jobs)
    all_jobs.sort(key=lambda j: j["posted_at"], reverse=True)

    print_summary(all_jobs)

    out = args.output
    if out.endswith(".json"):
        save_json(all_jobs, out)
    else:
        save_csv(all_jobs, out)


if __name__ == "__main__":
    main()
