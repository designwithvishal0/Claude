#!/usr/bin/env python3
"""
x_jobs_scraper.py
Scrapes job postings from X (Twitter) using the Twitter API v2.

Usage:
  python x_jobs_scraper.py [--query "..."] [--max 50] [--out jobs.json]

Requires:
  pip install tweepy requests python-dotenv

Set your credentials in a .env file:
  X_BEARER_TOKEN=your_bearer_token_here
"""

import os
import re
import json
import time
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

try:
    import tweepy
    from dotenv import load_dotenv
except ImportError:
    raise SystemExit("Missing dependencies. Run: pip install tweepy python-dotenv")

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("x_jobs")

# ---------------------------------------------------------------------------
# Default search queries — combine to cast a wide net
# ---------------------------------------------------------------------------
DEFAULT_QUERIES = [
    "we're hiring -is:retweet has:links lang:en",
    "job opening -is:retweet has:links lang:en",
    "#hiring #engineer -is:retweet",
    "#hiringnow software engineer -is:retweet lang:en",
    "we are hiring product manager -is:retweet lang:en",
    "open role designer -is:retweet has:links lang:en",
]

# ---------------------------------------------------------------------------
# Role classification heuristics
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS = {
    "engineering": ["engineer", "developer", "backend", "frontend", "fullstack", "devops",
                    "sre", "data", "ml", "machine learning", "ai", "platform", "infrastructure",
                    "golang", "python", "react", "typescript", "java", "rust"],
    "design":      ["designer", "ux", "ui", "product design", "visual design", "figma",
                    "research", "design lead"],
    "product":     ["product manager", "pm ", " pm,", "product lead", "head of product",
                    "vp product", "cpo"],
    "marketing":   ["marketing", "growth", "content", "seo", "demand gen", "brand",
                    "communications", "pr ", "devrel", "developer advocate", "community"],
    "sales":       ["sales", "account executive", "ae ", "sdr", "bdr", "revenue",
                    "partnerships", "business development", "bd "],
}

SIGNAL_KEYWORDS = {
    "hot":  ["we're hiring", "join our team", "now hiring", "#hiringnow", "urgent",
             "immediate", "apply now", "closing soon"],
    "warm": ["looking for", "open role", "open position", "job opening", "#hiring"],
    "cold": [],
}


def classify_category(text: str) -> str:
    t = text.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return cat
    return "other"


def classify_signal(text: str) -> str:
    t = text.lower()
    for signal, kws in SIGNAL_KEYWORDS.items():
        if kws and any(kw in t for kw in kws):
            return signal
    return "warm"


def extract_salary(text: str) -> str:
    patterns = [
        r"\$[\d,]+k?\s*[–\-]\s*\$[\d,]+k?",
        r"€[\d,]+k?\s*[–\-]\s*€[\d,]+k?",
        r"£[\d,]+k?\s*[–\-]\s*£[\d,]+k?",
        r"\$[\d,]+k\+?",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group()
    return "Salary not listed"


def extract_location(text: str) -> tuple[str, str]:
    remote_pats = [r"\bremote\b", r"\bwfh\b", r"work from anywhere", r"fully remote"]
    for p in remote_pats:
        if re.search(p, text, re.IGNORECASE):
            return "Remote", "remote"
    cities = {
        "san francisco": ("San Francisco, CA", "sf"),
        "new york": ("New York, NY", "ny"),
        "london": ("London, UK", "london"),
        "berlin": ("Berlin, Germany", "berlin"),
        "los angeles": ("Los Angeles, CA", "la"),
        "seattle": ("Seattle, WA", "seattle"),
        "austin": ("Austin, TX", "austin"),
        "boston": ("Boston, MA", "boston"),
    }
    t = text.lower()
    for kw, (label, key) in cities.items():
        if kw in t:
            return label, key
    return "Location TBD", "other"


def tweet_to_job(tweet, author) -> dict:
    text = tweet.text
    created = tweet.created_at.isoformat() if tweet.created_at else datetime.now(timezone.utc).isoformat()

    # human-readable age
    if tweet.created_at:
        delta = datetime.now(timezone.utc) - tweet.created_at.replace(tzinfo=timezone.utc)
        secs = int(delta.total_seconds())
        if secs < 3600:
            age = f"{secs // 60} min ago"
        elif secs < 86400:
            age = f"{secs // 3600} h ago"
        else:
            age = f"{secs // 86400} d ago"
    else:
        age = "recently"

    location, location_key = extract_location(text)
    category = classify_category(text)
    signal   = classify_signal(text)
    salary   = extract_salary(text)

    # engagement
    pm = tweet.public_metrics or {}
    likes     = pm.get("like_count", 0)
    retweets  = pm.get("retweet_count", 0)
    replies   = pm.get("reply_count", 0)

    # tags — extract hashtags
    tags = re.findall(r"#\w+", text)[:5]

    return {
        "id":           tweet.id,
        "handle":       f"@{author.username}" if author else "@unknown",
        "company":      author.name if author else "Unknown",
        "verified":     getattr(author, "verified", False),
        "role":         text.split("\n")[0][:100],
        "category":     category,
        "location":     location,
        "locationKey":  location_key,
        "type":         "Full-time",
        "salary":       salary,
        "postedAt":     age,
        "postedISO":    created,
        "postedKey":    "24h" if delta.total_seconds() < 86400 else "7d",
        "likes":        likes,
        "retweets":     retweets,
        "replies":      replies,
        "tags":         tags or ["#hiring"],
        "tweetExcerpt": text[:280],
        "tweetUrl":     f"https://x.com/{author.username}/status/{tweet.id}" if author else "#",
        "applyUrl":     f"https://x.com/{author.username}/status/{tweet.id}" if author else "#",
        "leadSignal":   signal,
        "scrapedAt":    datetime.now(timezone.utc).isoformat(),
    }


def scrape(queries: list[str], max_results: int = 50) -> list[dict]:
    bearer = os.getenv("X_BEARER_TOKEN")
    if not bearer:
        raise ValueError("X_BEARER_TOKEN not set. Add it to your .env file.")

    client = tweepy.Client(bearer_token=bearer, wait_on_rate_limit=True)
    jobs = []
    seen = set()

    for query in queries:
        log.info(f"Searching: {query!r}")
        try:
            response = client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),
                tweet_fields=["created_at", "public_metrics", "author_id", "entities"],
                user_fields=["name", "username", "verified"],
                expansions=["author_id"],
            )
        except tweepy.TooManyRequests:
            log.warning("Rate limited — sleeping 60s")
            time.sleep(60)
            continue
        except tweepy.TweepyException as e:
            log.error(f"API error: {e}")
            continue

        if not response.data:
            log.info("  No results.")
            continue

        users = {u.id: u for u in (response.includes.get("users") or [])}

        for tweet in response.data:
            if tweet.id in seen:
                continue
            seen.add(tweet.id)
            author = users.get(tweet.author_id)
            job = tweet_to_job(tweet, author)
            jobs.append(job)
            log.info(f"  + [{job['category']:11s}] {job['company']} — {job['role'][:60]}")

        time.sleep(1)

    return jobs


def main():
    parser = argparse.ArgumentParser(description="Scrape job posts from X")
    parser.add_argument("--query",  default=None,        help="Custom search query (overrides defaults)")
    parser.add_argument("--max",    type=int, default=50, help="Max results per query (default 50)")
    parser.add_argument("--out",    default="jobs.json",  help="Output file (default jobs.json)")
    parser.add_argument("--append", action="store_true",  help="Append to existing output file")
    args = parser.parse_args()

    queries = [args.query] if args.query else DEFAULT_QUERIES

    log.info(f"Starting X jobs scraper — {len(queries)} quer{'y' if len(queries)==1 else 'ies'}")
    jobs = scrape(queries, max_results=args.max)
    log.info(f"Scraped {len(jobs)} job posts")

    out_path = Path(args.out)
    existing = []
    if args.append and out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
        except json.JSONDecodeError:
            pass

    all_jobs = existing + jobs
    # deduplicate by tweet id
    seen_ids = set()
    deduped = []
    for j in all_jobs:
        if j["id"] not in seen_ids:
            seen_ids.add(j["id"])
            deduped.append(j)

    out_path.write_text(json.dumps(deduped, indent=2, ensure_ascii=False))
    log.info(f"Saved {len(deduped)} jobs → {out_path}")


if __name__ == "__main__":
    main()
