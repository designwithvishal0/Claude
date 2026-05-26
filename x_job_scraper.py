"""
X (Twitter) Job Scraper
Scrapes job postings from X using the official API (Tweepy) or
a keyword/hashtag search approach.

Requirements:
    pip install tweepy pandas requests python-dotenv
"""

import os
import csv
import json
import time
import re
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class JobPost:
    tweet_id: str
    author: str
    author_handle: str
    created_at: str
    text: str
    url: str
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    hashtags: list = field(default_factory=list)
    job_title: str = ""
    company: str = ""
    location: str = ""
    remote: bool = False
    salary: str = ""


# ── Helpers ───────────────────────────────────────────────────────────────────

JOB_KEYWORDS = [
    "#hiring", "#nowhiring", "#jobsearch", "#jobs", "#remotejobs",
    "#techjobs", "#engineeringjobs", "#designjobs", "#productjobs",
    "we are hiring", "we're hiring", "join our team",
    "open role", "open position", "job opening",
]

REMOTE_SIGNALS = ["remote", "work from home", "wfh", "distributed", "anywhere"]

SALARY_PATTERN = re.compile(
    r"[\$£€]?\s*\d[\d,]*[kK]?\s*(?:[-–]\s*[\$£€]?\s*\d[\d,]*[kK]?)?"
    r"\s*(?:per\s+(?:year|annum|month)|\/(?:yr|mo|hr|hour))?",
    re.IGNORECASE,
)

TITLE_PATTERNS = [
    re.compile(r"(?:hiring|looking for|seeking)\s+(?:a\s+)?([A-Z][^\n,!?.]{3,50})", re.IGNORECASE),
    re.compile(r"role\s*:\s*([^\n,!?]{3,50})", re.IGNORECASE),
    re.compile(r"position\s*:\s*([^\n,!?]{3,50})", re.IGNORECASE),
]

COMPANY_PATTERN = re.compile(r"@([A-Za-z0-9_]+)\s+is\s+hiring", re.IGNORECASE)


def extract_job_fields(text: str) -> dict:
    """Best-effort extraction of structured fields from a tweet."""
    data: dict = {"job_title": "", "company": "", "location": "", "remote": False, "salary": ""}

    for pat in TITLE_PATTERNS:
        m = pat.search(text)
        if m:
            data["job_title"] = m.group(1).strip()
            break

    m = COMPANY_PATTERN.search(text)
    if m:
        data["company"] = m.group(1)

    salary_matches = SALARY_PATTERN.findall(text)
    if salary_matches:
        data["salary"] = salary_matches[0].strip()

    lower = text.lower()
    data["remote"] = any(sig in lower for sig in REMOTE_SIGNALS)

    loc_match = re.search(
        r"(?:based in|location\s*[:\-]?)\s*([A-Z][a-zA-Z\s,]{2,40})", text, re.IGNORECASE
    )
    if loc_match:
        data["location"] = loc_match.group(1).strip()

    return data


def tweet_url(handle: str, tweet_id: str) -> str:
    return f"https://x.com/{handle}/status/{tweet_id}"


# ── Scraper (Tweepy / Official API v2) ───────────────────────────────────────

class XJobScraper:
    """
    Uses the X API v2 (Bearer Token) to search recent tweets.
    Free tier: 1 request / 15 min, ~10 tweets.
    Basic tier ($100/mo): 60 requests / 15 min, up to 10 000 tweets / month.
    """

    def __init__(self, bearer_token: Optional[str] = None):
        self.bearer_token = bearer_token or os.getenv("X_BEARER_TOKEN")
        self.client = None

        if self.bearer_token:
            try:
                import tweepy  # noqa: PLC0415
                self.client = tweepy.Client(bearer_token=self.bearer_token, wait_on_rate_limit=True)
                print("[✓] Tweepy client initialised with Bearer Token.")
            except ImportError:
                print("[!] tweepy not installed. Run: pip install tweepy")
        else:
            print("[!] X_BEARER_TOKEN not set — falling back to demo mode.")

    # ── Public API ────────────────────────────────────────────────────────────

    def scrape(
        self,
        keywords: Optional[list[str]] = None,
        max_results: int = 100,
        output_format: str = "csv",  # "csv" | "json"
        output_file: str = "x_jobs",
    ) -> list[JobPost]:
        """Scrape job postings and save results."""
        keywords = keywords or JOB_KEYWORDS[:5]
        query = self._build_query(keywords)
        print(f"[→] Query: {query}")

        if self.client:
            posts = self._search_api(query, max_results)
        else:
            posts = self._demo_posts()

        print(f"[✓] Found {len(posts)} job posts.")
        self._save(posts, output_format, output_file)
        return posts

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_query(self, keywords: list[str]) -> str:
        kw_part = " OR ".join(f'"{kw}"' for kw in keywords)
        return f"({kw_part}) -is:retweet lang:en"

    def _search_api(self, query: str, max_results: int) -> list[JobPost]:
        import tweepy  # noqa: PLC0415

        posts: list[JobPost] = []
        tweet_fields = ["created_at", "public_metrics", "entities", "author_id"]
        expansions = ["author_id"]
        user_fields = ["name", "username"]

        try:
            paginator = tweepy.Paginator(
                self.client.search_recent_tweets,
                query=query,
                tweet_fields=tweet_fields,
                expansions=expansions,
                user_fields=user_fields,
                max_results=min(max_results, 100),
            ).flatten(limit=max_results)

            # Build user lookup from includes
            users: dict[str, tuple[str, str]] = {}

            for tweet in paginator:
                # tweepy Paginator.flatten yields Tweet objects
                uid = str(tweet.author_id)
                if uid not in users:
                    # fetch user lazily — already expanded in response
                    users[uid] = (uid, uid)

                author_name, author_handle = users.get(uid, (uid, uid))
                metrics = tweet.public_metrics or {}
                hashtags = [
                    tag["tag"]
                    for tag in (tweet.entities or {}).get("hashtags", [])
                ]
                extra = extract_job_fields(tweet.text)

                posts.append(JobPost(
                    tweet_id=str(tweet.id),
                    author=author_name,
                    author_handle=author_handle,
                    created_at=str(tweet.created_at),
                    text=tweet.text,
                    url=tweet_url(author_handle, str(tweet.id)),
                    likes=metrics.get("like_count", 0),
                    retweets=metrics.get("retweet_count", 0),
                    replies=metrics.get("reply_count", 0),
                    hashtags=hashtags,
                    **extra,
                ))
                time.sleep(0.05)

        except Exception as exc:
            print(f"[!] API error: {exc}")

        return posts

    def _demo_posts(self) -> list[JobPost]:
        """Returns a small set of synthetic posts when no API key is provided."""
        samples = [
            {
                "tweet_id": "1234567890001",
                "author": "TechCorp Careers",
                "author_handle": "techcorpcareers",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "text": "We're #hiring a Senior Python Engineer! Remote-friendly, $130K-$160K/yr. Join our team! #remotejobs #techjobs",
                "url": "https://x.com/techcorpcareers/status/1234567890001",
                "likes": 45, "retweets": 12, "replies": 3,
                "hashtags": ["hiring", "remotejobs", "techjobs"],
                "job_title": "Senior Python Engineer",
                "company": "TechCorp",
                "location": "",
                "remote": True,
                "salary": "$130K-$160K/yr",
            },
            {
                "tweet_id": "1234567890002",
                "author": "DesignStudio",
                "author_handle": "designstudiohq",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "text": "Open role: Product Designer. Based in New York or remote. We are hiring! #designjobs #nowhiring",
                "url": "https://x.com/designstudiohq/status/1234567890002",
                "likes": 30, "retweets": 8, "replies": 5,
                "hashtags": ["designjobs", "nowhiring"],
                "job_title": "Product Designer",
                "company": "DesignStudio",
                "location": "New York",
                "remote": True,
                "salary": "",
            },
            {
                "tweet_id": "1234567890003",
                "author": "StartupXYZ",
                "author_handle": "startupxyz",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "text": "Join our team as a Marketing Manager! Location: San Francisco. Salary: $90K-$110K. #hiring #jobs",
                "url": "https://x.com/startupxyz/status/1234567890003",
                "likes": 22, "retweets": 5, "replies": 2,
                "hashtags": ["hiring", "jobs"],
                "job_title": "Marketing Manager",
                "company": "StartupXYZ",
                "location": "San Francisco",
                "remote": False,
                "salary": "$90K-$110K",
            },
        ]
        return [JobPost(**s) for s in samples]

    # ── Output ────────────────────────────────────────────────────────────────

    def _save(self, posts: list[JobPost], fmt: str, base: str) -> None:
        if fmt == "json":
            path = f"{base}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump([asdict(p) for p in posts], f, indent=2, ensure_ascii=False)
            print(f"[✓] Saved {len(posts)} records → {path}")

        else:  # csv (default)
            path = f"{base}.csv"
            if not posts:
                print("[!] No posts to save.")
                return
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(asdict(posts[0]).keys()))
                writer.writeheader()
                for p in posts:
                    row = asdict(p)
                    row["hashtags"] = ", ".join(row["hashtags"])
                    writer.writerow(row)
            print(f"[✓] Saved {len(posts)} records → {path}")


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape job postings from X (Twitter).")
    parser.add_argument("--keywords", nargs="+", default=None,
                        help="Custom keywords/hashtags to search (e.g. '#hiring' 'we are hiring')")
    parser.add_argument("--max", type=int, default=100, dest="max_results",
                        help="Maximum number of tweets to fetch (default: 100)")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", dest="output_format",
                        help="Output format: csv or json (default: csv)")
    parser.add_argument("--output", default="x_jobs", dest="output_file",
                        help="Output filename without extension (default: x_jobs)")
    parser.add_argument("--token", default=None,
                        help="X Bearer Token (overrides X_BEARER_TOKEN env var)")
    args = parser.parse_args()

    scraper = XJobScraper(bearer_token=args.token)
    results = scraper.scrape(
        keywords=args.keywords,
        max_results=args.max_results,
        output_format=args.output_format,
        output_file=args.output_file,
    )

    # Print a quick preview
    print("\n── Preview (first 5) ──────────────────────────────")
    for p in results[:5]:
        print(f"  [{p.created_at[:10]}] @{p.author_handle} | {p.job_title or '(no title)'} | remote={p.remote} | {p.salary or 'no salary'}")
        print(f"  {p.url}")
        print()
