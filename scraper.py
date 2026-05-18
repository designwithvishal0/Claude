"""
X (Twitter) Job Scraper
Searches X for job postings via the X API v2 and saves results to CSV/JSON.
Requires a Bearer Token from https://developer.twitter.com/
"""

import os
import csv
import json
import time
import argparse
from datetime import datetime, timezone
from typing import Optional

import requests

BASE_URL = "https://api.twitter.com/2"
DEFAULT_QUERIES = [
    "hiring remote",
    "we are hiring",
    "job opening",
    "software engineer hiring",
    "looking for developer",
]


def search_jobs(
    bearer_token: str,
    query: str,
    max_results: int = 100,
    start_time: Optional[str] = None,
) -> list[dict]:
    """Search X for job-related posts matching the query."""
    headers = {"Authorization": f"Bearer {bearer_token}"}
    params = {
        "query": f"{query} -is:retweet lang:en",
        "max_results": min(max_results, 100),
        "tweet.fields": "created_at,author_id,public_metrics,entities",
        "expansions": "author_id",
        "user.fields": "name,username,description,location,verified",
    }
    if start_time:
        params["start_time"] = start_time

    all_posts: list[dict] = []
    next_token = None

    while len(all_posts) < max_results:
        if next_token:
            params["next_token"] = next_token

        response = requests.get(
            f"{BASE_URL}/tweets/search/recent",
            headers=headers,
            params=params,
            timeout=30,
        )

        if response.status_code == 429:
            reset = int(response.headers.get("x-rate-limit-reset", time.time() + 60))
            wait = max(reset - int(time.time()), 1)
            print(f"  Rate limited — waiting {wait}s...")
            time.sleep(wait)
            continue

        response.raise_for_status()
        data = response.json()

        tweets = data.get("data", [])
        if not tweets:
            break

        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

        for tweet in tweets:
            author = users.get(tweet.get("author_id"), {})
            metrics = tweet.get("public_metrics", {})
            urls = [
                u.get("expanded_url", "")
                for u in tweet.get("entities", {}).get("urls", [])
                if u.get("expanded_url")
            ]
            all_posts.append(
                {
                    "id": tweet["id"],
                    "created_at": tweet.get("created_at", ""),
                    "text": tweet["text"].replace("\n", " "),
                    "author_name": author.get("name", ""),
                    "author_username": author.get("username", ""),
                    "author_location": author.get("location", ""),
                    "author_verified": author.get("verified", False),
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "urls": " | ".join(urls),
                    "query": query,
                    "post_url": f"https://x.com/{author.get('username', '')}/status/{tweet['id']}",
                }
            )

        meta = data.get("meta", {})
        next_token = meta.get("next_token")
        if not next_token or len(tweets) < params["max_results"]:
            break

    return all_posts


def save_csv(posts: list[dict], path: str) -> None:
    if not posts:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=posts[0].keys())
        writer.writeheader()
        writer.writerows(posts)


def save_json(posts: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape job postings from X (Twitter)")
    parser.add_argument(
        "--token",
        default=os.environ.get("X_BEARER_TOKEN"),
        help="X API v2 Bearer Token (or set X_BEARER_TOKEN env var)",
    )
    parser.add_argument(
        "--queries",
        nargs="+",
        default=DEFAULT_QUERIES,
        help="Search queries to run (default: common hiring phrases)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=100,
        help="Max posts per query (default: 100)",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="Only return posts after this ISO 8601 timestamp (e.g. 2024-01-01T00:00:00Z)",
    )
    parser.add_argument(
        "--output",
        default="jobs",
        help="Output filename without extension (default: jobs)",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json", "both"],
        default="both",
        help="Output format (default: both)",
    )
    args = parser.parse_args()

    if not args.token:
        parser.error(
            "Bearer token required. Pass --token or set the X_BEARER_TOKEN environment variable.\n"
            "Get one at https://developer.twitter.com/"
        )

    all_posts: list[dict] = []
    for query in args.queries:
        print(f"Searching: '{query}'...")
        try:
            posts = search_jobs(args.token, query, args.max_results, args.since)
            print(f"  Found {len(posts)} posts")
            all_posts.extend(posts)
        except requests.HTTPError as e:
            print(f"  Error for query '{query}': {e}")

    # Deduplicate by tweet ID
    seen: set[str] = set()
    unique = [p for p in all_posts if not (p["id"] in seen or seen.add(p["id"]))]  # type: ignore[func-returns-value]
    print(f"\nTotal unique posts: {len(unique)}")

    if not unique:
        print("No posts found — nothing to save.")
        return

    if args.format in ("csv", "both"):
        path = f"{args.output}.csv"
        save_csv(unique, path)
        print(f"Saved CSV  → {path}")

    if args.format in ("json", "both"):
        path = f"{args.output}.json"
        save_json(unique, path)
        print(f"Saved JSON → {path}")


if __name__ == "__main__":
    main()
