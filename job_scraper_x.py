"""
job_scraper_x.py — scrape job postings from X (Twitter) via API v2

Requirements:
    pip install tweepy requests

Setup:
    Export your X API Bearer Token before running:
        export X_BEARER_TOKEN="your_bearer_token_here"

    Get a token at: https://developer.x.com/en/portal/dashboard

Usage:
    python job_scraper_x.py
    python job_scraper_x.py --query "#hiring python" --max 50
    python job_scraper_x.py --output jobs.json
"""

import os
import sys
import json
import argparse
import re
from datetime import datetime, timezone

try:
    import tweepy
except ImportError:
    sys.exit("Install tweepy first:  pip install tweepy")


DEFAULT_QUERIES = [
    "#hiring #python",
    "#hiring #javascript",
    "#nowhiring #react",
    "#hiring #remotejobs",
    "#techJobs #hiring",
    "we're hiring (software OR engineer OR developer) -is:retweet lang:en",
]

SALARY_RE = re.compile(r'\$[\d,]+[kK]?(?:\s*[-–]\s*\$?[\d,]+[kK]?)?(?:/(?:yr|year|hr|hour|mo|month))?')


def parse_args():
    p = argparse.ArgumentParser(description="Scrape job posts from X (Twitter)")
    p.add_argument("--query",  default=None, help="Custom search query (overrides defaults)")
    p.add_argument("--max",    type=int, default=100, help="Max tweets per query (10–500)")
    p.add_argument("--output", default="jobs_x.json", help="Output JSON file path")
    p.add_argument("--days",   type=int, default=7, help="Look back N days (max 7 for free tier)")
    return p.parse_args()


def get_client():
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        sys.exit(
            "X_BEARER_TOKEN is not set.\n"
            "  export X_BEARER_TOKEN='your_token'\n"
            "  Get one at https://developer.x.com/en/portal/dashboard"
        )
    return tweepy.Client(bearer_token=token, wait_on_rate_limit=True)


def extract_salary(text):
    m = SALARY_RE.search(text)
    return m.group(0) if m else None


def extract_location(text):
    patterns = [
        r'\b(remote|wfh|work from home)\b',
        r'\b([A-Z][a-z]+(?:,\s*[A-Z]{2})?)\b',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            loc = m.group(0).strip()
            if loc.lower() in ("remote", "wfh", "work from home"):
                return "Remote"
            if len(loc) > 3:
                return loc
    return None


def search_jobs(client, query, max_results, since_days):
    tweet_fields = ["created_at", "author_id", "text", "public_metrics", "entities"]
    user_fields  = ["name", "username", "verified"]
    expansions   = ["author_id"]

    results = []
    try:
        paginator = tweepy.Paginator(
            client.search_recent_tweets,
            query=f"{query} -is:retweet lang:en",
            tweet_fields=tweet_fields,
            user_fields=user_fields,
            expansions=expansions,
            max_results=min(max_results, 100),
        )

        users_by_id = {}
        tweet_count = 0

        for page in paginator:
            if page.includes and "users" in page.includes:
                for u in page.includes["users"]:
                    users_by_id[u.id] = u

            if not page.data:
                continue

            for tweet in page.data:
                if tweet_count >= max_results:
                    break
                tweet_count += 1

                author = users_by_id.get(tweet.author_id)
                urls = []
                if tweet.entities and "urls" in tweet.entities:
                    urls = [u["expanded_url"] for u in tweet.entities["urls"]
                            if "twitter.com" not in u.get("expanded_url", "")]

                results.append({
                    "id":          tweet.id,
                    "text":        tweet.text,
                    "author_name": author.name if author else None,
                    "author_handle": f"@{author.username}" if author else None,
                    "created_at":  tweet.created_at.isoformat() if tweet.created_at else None,
                    "likes":       tweet.public_metrics.get("like_count", 0) if tweet.public_metrics else 0,
                    "retweets":    tweet.public_metrics.get("retweet_count", 0) if tweet.public_metrics else 0,
                    "salary":      extract_salary(tweet.text),
                    "location":    extract_location(tweet.text),
                    "apply_urls":  urls,
                    "tweet_url":   f"https://x.com/i/web/status/{tweet.id}",
                    "query":       query,
                    "source":      "X (Twitter)",
                })

            if tweet_count >= max_results:
                break

    except tweepy.errors.TooManyRequests:
        print(f"  Rate limited on query: {query!r} — partial results returned")
    except tweepy.errors.Forbidden as e:
        print(f"  Access denied for query {query!r}: {e}")
    except tweepy.errors.TweepyException as e:
        print(f"  Error on query {query!r}: {e}")

    return results


def deduplicate(jobs):
    seen = set()
    out = []
    for j in jobs:
        if j["id"] not in seen:
            seen.add(j["id"])
            out.append(j)
    return out


def main():
    args = parse_args()
    client = get_client()

    queries = [args.query] if args.query else DEFAULT_QUERIES
    all_jobs = []

    print(f"Scraping X for job posts ({len(queries)} quer{'y' if len(queries)==1 else 'ies'})…")
    for q in queries:
        print(f"  Searching: {q!r}")
        jobs = search_jobs(client, q, args.max, args.days)
        print(f"    → {len(jobs)} posts found")
        all_jobs.extend(jobs)

    all_jobs = deduplicate(all_jobs)
    all_jobs.sort(key=lambda j: (j.get("likes", 0) + j.get("retweets", 0) * 2), reverse=True)

    output = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "total":      len(all_jobs),
        "source":     "X (Twitter)",
        "jobs":       all_jobs,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nDone — {len(all_jobs)} unique job posts saved to {args.output!r}")

    if all_jobs:
        print("\nTop 3 by engagement:")
        for j in all_jobs[:3]:
            print(f"  [{j['likes']} likes] {j['author_handle']} — {j['text'][:80].strip()}…")
            if j['apply_urls']:
                print(f"    Apply: {j['apply_urls'][0]}")


if __name__ == "__main__":
    main()
