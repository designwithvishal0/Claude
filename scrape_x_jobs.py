#!/usr/bin/env python3
"""
X (Twitter) Job Post Scraper
Searches X for job postings using job-related hashtags and saves structured JSON.

Usage:
  python scrape_x_jobs.py                  # scrape with default queries
  python scrape_x_jobs.py --query "#SWE"   # custom query
  python scrape_x_jobs.py --demo           # output sample data (no auth needed)
  python scrape_x_jobs.py --token YOUR_TOKEN  # use your own bearer token
"""

import requests
import json
import time
import re
import sys
import argparse
from datetime import datetime, timezone

# X's public bearer token (embedded in web app, used for unauthenticated guest access)
DEFAULT_BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I%2BxouJiPA"
    "AAAAGkJJ8g%3Dsg3J6Tik8bSTjfxrpNKJHOoZDoxz7d5nERKcMHqsKMHqM"
)

JOB_QUERIES = [
    "#hiring #remote lang:en",
    "#NowHiring #tech lang:en",
    "#JobOpening #engineering lang:en",
    "#StartupJobs lang:en",
    "#TechJobs #2025 lang:en",
    "\"we're hiring\" #engineering -is:retweet lang:en",
    "#RemoteWork #hiring -is:retweet lang:en",
]

JOB_SIGNALS = {
    "hiring", "job", "position", "role", "opportunity", "career",
    "apply", "join our team", "we're looking", "open role", "open position",
    "software engineer", "developer", "designer", "product manager",
    "full-time", "full time", "part-time", "contract", "intern",
    "salary", "remote", "on-site", "hybrid", "benefits",
}

TITLE_PATTERNS = [
    r"(?:hiring|looking for|seeking)[a\s]+([A-Z][a-zA-Z\s]+?(?:Engineer|Developer|Designer|Manager|Director|Lead|Analyst|Architect|Scientist|Marketer|Writer|Researcher|Recruiter))\b",
    r"\b([A-Z][a-zA-Z\s]*?(?:Engineer|Developer|Designer|Manager|Director|Lead|Analyst|Architect|Scientist))\s+(?:role|position|job|opening|opportunity)\b",
    r"(?:open role|open position|job opening)[:\s]+([A-Za-z][a-zA-Z\s\-\/]+)",
]

LOCATION_PATTERNS = [
    r"\b(Remote|Hybrid|On-?site)\b",
    r"(?:located in|based in|location[:\s]+)([A-Z][a-zA-Z\s,]+?)(?:\n|#|\.|!)",
    r"\b([A-Z][a-zA-Z]+,\s*(?:CA|NY|TX|WA|UK|US|EU|AUS|CAN))\b",
]


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _headers(bearer: str, guest_token: str | None = None) -> dict:
    h = {
        "Authorization": f"Bearer {bearer}",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://x.com/",
    }
    if guest_token:
        h["x-guest-token"] = guest_token
    return h


def get_guest_token(bearer: str) -> str:
    resp = requests.post(
        "https://api.twitter.com/1.1/guest/activate.json",
        headers=_headers(bearer),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["guest_token"]


def search_v1(query: str, bearer: str, guest_token: str, count: int = 100) -> list[dict]:
    resp = requests.get(
        "https://api.twitter.com/1.1/search/tweets.json",
        headers=_headers(bearer, guest_token),
        params={
            "q": query,
            "count": count,
            "result_type": "recent",
            "tweet_mode": "extended",
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json().get("statuses", [])


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def extract_title(text: str) -> str:
    for pat in TITLE_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:80]
    return "Job Opening"


def extract_location(text: str, user: dict) -> str:
    if user.get("location"):
        return user["location"]
    for pat in LOCATION_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return "Remote / Not specified"


def is_job_post(tweet: dict) -> bool:
    text = tweet.get("full_text", tweet.get("text", "")).lower()
    return any(sig in text for sig in JOB_SIGNALS)


def parse_tweet(tweet: dict) -> dict:
    text = tweet.get("full_text", tweet.get("text", ""))
    user = tweet.get("user", {})
    hashtags = [h["text"] for h in tweet.get("entities", {}).get("hashtags", [])]
    return {
        "id": tweet["id_str"],
        "text": text,
        "company": user.get("name", "Unknown"),
        "handle": "@" + user.get("screen_name", "unknown"),
        "avatar_color": _avatar_color(user.get("screen_name", "")),
        "initials": _initials(user.get("name", "?")),
        "verified": user.get("verified", False) or user.get("is_blue_verified", False),
        "followers": user.get("followers_count", 0),
        "title": extract_title(text),
        "location": extract_location(text, user),
        "hashtags": hashtags[:6],
        "likes": tweet.get("favorite_count", 0),
        "retweets": tweet.get("retweet_count", 0),
        "replies": tweet.get("reply_count", 0),
        "url": f"https://x.com/{user.get('screen_name','')}/status/{tweet['id_str']}",
        "created_at": tweet.get("created_at", ""),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def _initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "?"


AVATAR_COLORS = [
    "#6366F1", "#8B5CF6", "#EC4899", "#EF4444",
    "#F59E0B", "#10B981", "#3B82F6", "#14B8A6",
]


def _avatar_color(handle: str) -> str:
    return AVATAR_COLORS[hash(handle) % len(AVATAR_COLORS)]


# ---------------------------------------------------------------------------
# Main scraper
# ---------------------------------------------------------------------------

def scrape(queries: list[str], bearer: str, count_per_query: int = 50) -> list[dict]:
    print("Authenticating with X (guest token)…", file=sys.stderr)
    try:
        guest_token = get_guest_token(bearer)
        print(f"Guest token acquired.", file=sys.stderr)
    except Exception as exc:
        print(f"Auth failed: {exc}", file=sys.stderr)
        print("Falling back to demo data.", file=sys.stderr)
        return demo_jobs()

    seen: set[str] = set()
    jobs: list[dict] = []

    for q in queries:
        print(f"Searching: {q}", file=sys.stderr)
        try:
            tweets = search_v1(q, bearer, guest_token, count=count_per_query)
            print(f"  {len(tweets)} tweets returned", file=sys.stderr)
            for tw in tweets:
                if tw.get("retweeted_status"):
                    continue
                if tw["id_str"] in seen:
                    continue
                if not is_job_post(tw):
                    continue
                seen.add(tw["id_str"])
                jobs.append(parse_tweet(tw))
            time.sleep(1.5)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response else "?"
            print(f"  HTTP {status} – skipping query", file=sys.stderr)
            if status == 429:
                print("  Rate-limited; waiting 60s…", file=sys.stderr)
                time.sleep(60)
        except Exception as exc:
            print(f"  Error: {exc}", file=sys.stderr)

    if not jobs:
        print("No jobs found via API; using demo data.", file=sys.stderr)
        return demo_jobs()

    return jobs


# ---------------------------------------------------------------------------
# Demo data (used when API is unavailable or --demo flag is set)
# ---------------------------------------------------------------------------

def demo_jobs() -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "id": "demo_001",
            "text": "We're hiring a Senior Software Engineer (Remote)!\n\nLooking for someone who loves distributed systems and can work across the full stack. 5+ yrs experience, competitive salary + equity.\n\n#hiring #remote #SoftwareEngineer #TechJobs\n\nApply: careers.acme.io/swe",
            "company": "Acme Corp",
            "handle": "@AcmeCorpHQ",
            "avatar_color": "#6366F1",
            "initials": "AC",
            "verified": True,
            "followers": 24800,
            "title": "Senior Software Engineer",
            "location": "Remote",
            "hashtags": ["hiring", "remote", "SoftwareEngineer", "TechJobs"],
            "likes": 312, "retweets": 87, "replies": 23,
            "url": "https://x.com/AcmeCorpHQ/status/demo_001",
            "created_at": "Fri Jun 27 09:14:00 +0000 2025",
            "scraped_at": now,
        },
        {
            "id": "demo_002",
            "text": "🚀 NovaTech is looking for a Product Designer to join our growing team!\n\nYou'll shape the UX of our AI-powered analytics platform. Hybrid — Austin, TX.\n\nSalary: $120k–$150k + options\n#ProductDesign #NowHiring #Austin #DesignJobs",
            "company": "NovaTech",
            "handle": "@NovaTechAI",
            "avatar_color": "#8B5CF6",
            "initials": "NT",
            "verified": False,
            "followers": 8300,
            "title": "Product Designer",
            "location": "Austin, TX (Hybrid)",
            "hashtags": ["ProductDesign", "NowHiring", "Austin", "DesignJobs"],
            "likes": 201, "retweets": 55, "replies": 14,
            "url": "https://x.com/NovaTechAI/status/demo_002",
            "created_at": "Fri Jun 27 07:30:00 +0000 2025",
            "scraped_at": now,
        },
        {
            "id": "demo_003",
            "text": "Open role: ML Engineer @ Vertex AI startup (Series B)\n\nWe're building next-gen speech models. Looking for someone fluent in PyTorch and ideally familiar with ASR research.\n\nFull remote. $160k–$200k.\n#MLEngineer #MachineLearning #hiring #StartupJobs",
            "company": "Vertex Speech",
            "handle": "@VertexSpeechAI",
            "avatar_color": "#10B981",
            "initials": "VS",
            "verified": False,
            "followers": 3100,
            "title": "ML Engineer",
            "location": "Remote",
            "hashtags": ["MLEngineer", "MachineLearning", "hiring", "StartupJobs"],
            "likes": 445, "retweets": 134, "replies": 38,
            "url": "https://x.com/VertexSpeechAI/status/demo_003",
            "created_at": "Thu Jun 26 18:02:00 +0000 2025",
            "scraped_at": now,
        },
        {
            "id": "demo_004",
            "text": "Founding Engineer position open at CloudShift!\n\nYou'll be employee #7, shaping architecture from day one. React + Go stack, K8s. Seed funded.\n\nSan Francisco or Remote.\n#hiring #FoundingEngineer #startup #TechJobs",
            "company": "CloudShift",
            "handle": "@CloudShiftHQ",
            "avatar_color": "#3B82F6",
            "initials": "CS",
            "verified": False,
            "followers": 1240,
            "title": "Founding Engineer",
            "location": "San Francisco / Remote",
            "hashtags": ["hiring", "FoundingEngineer", "startup", "TechJobs"],
            "likes": 677, "retweets": 189, "replies": 62,
            "url": "https://x.com/CloudShiftHQ/status/demo_004",
            "created_at": "Thu Jun 26 14:45:00 +0000 2025",
            "scraped_at": now,
        },
        {
            "id": "demo_005",
            "text": "DevRel Engineer wanted! Join our open-source-first team at PulseDB.\n\nYou'll write docs, build demos, speak at conferences, and be the bridge between community and engineering.\n\nFully remote · $110k–$140k\n#DevRel #hiring #OpenSource #remote",
            "company": "PulseDB",
            "handle": "@PulseDBio",
            "avatar_color": "#EC4899",
            "initials": "PD",
            "verified": False,
            "followers": 6700,
            "title": "DevRel Engineer",
            "location": "Remote",
            "hashtags": ["DevRel", "hiring", "OpenSource", "remote"],
            "likes": 388, "retweets": 101, "replies": 29,
            "url": "https://x.com/PulseDBio/status/demo_005",
            "created_at": "Thu Jun 26 11:20:00 +0000 2025",
            "scraped_at": now,
        },
        {
            "id": "demo_006",
            "text": "We're hiring a Growth Marketing Manager at ScaleUp!\n\nOwn our demand-gen strategy: paid, SEO, email, partnerships. 3+ yrs B2B SaaS experience needed.\n\nNew York, NY (Hybrid)\n#MarketingJobs #NowHiring #GrowthMarketing #B2BSaaS",
            "company": "ScaleUp",
            "handle": "@ScaleUpHQ",
            "avatar_color": "#F59E0B",
            "initials": "SU",
            "verified": True,
            "followers": 18900,
            "title": "Growth Marketing Manager",
            "location": "New York, NY (Hybrid)",
            "hashtags": ["MarketingJobs", "NowHiring", "GrowthMarketing", "B2BSaaS"],
            "likes": 156, "retweets": 42, "replies": 11,
            "url": "https://x.com/ScaleUpHQ/status/demo_006",
            "created_at": "Wed Jun 25 20:15:00 +0000 2025",
            "scraped_at": now,
        },
        {
            "id": "demo_007",
            "text": "Backend Engineer (Rust) — DataStream is hiring!\n\nBuilding high-throughput event streaming infra. You'll write production Rust, design APIs, and care deeply about latency.\n\nRemote-first. Series A. Comp: $170k–$210k\n#RustLang #BackendDev #hiring #remote",
            "company": "DataStream",
            "handle": "@DataStreamIO",
            "avatar_color": "#EF4444",
            "initials": "DS",
            "verified": False,
            "followers": 4500,
            "title": "Backend Engineer (Rust)",
            "location": "Remote",
            "hashtags": ["RustLang", "BackendDev", "hiring", "remote"],
            "likes": 522, "retweets": 143, "replies": 47,
            "url": "https://x.com/DataStreamIO/status/demo_007",
            "created_at": "Wed Jun 25 16:40:00 +0000 2025",
            "scraped_at": now,
        },
        {
            "id": "demo_008",
            "text": "Senior Product Manager opening at BrightPath Health!\n\nLead our patient-facing mobile product. You'll work with doctors, engineers, and designers to ship features that matter.\n\nBoston, MA (On-site)\n#ProductManagement #HealthTech #PM #hiring",
            "company": "BrightPath Health",
            "handle": "@BrightPathHealth",
            "avatar_color": "#14B8A6",
            "initials": "BP",
            "verified": False,
            "followers": 7200,
            "title": "Senior Product Manager",
            "location": "Boston, MA",
            "hashtags": ["ProductManagement", "HealthTech", "PM", "hiring"],
            "likes": 234, "retweets": 67, "replies": 19,
            "url": "https://x.com/BrightPathHealth/status/demo_008",
            "created_at": "Tue Jun 24 13:10:00 +0000 2025",
            "scraped_at": now,
        },
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scrape job posts from X (Twitter)")
    parser.add_argument("--query", metavar="Q", help="Custom search query (replaces default queries)")
    parser.add_argument("--count", type=int, default=50, metavar="N", help="Max tweets per query (default 50)")
    parser.add_argument("--output", default="x_jobs.json", metavar="FILE", help="Output JSON file (default x_jobs.json)")
    parser.add_argument("--token", metavar="BEARER", help="Custom bearer token (overrides built-in)")
    parser.add_argument("--demo", action="store_true", help="Skip scraping; output built-in demo data")
    args = parser.parse_args()

    bearer = args.token or DEFAULT_BEARER
    queries = [args.query] if args.query else JOB_QUERIES

    if args.demo:
        jobs = demo_jobs()
    else:
        jobs = scrape(queries, bearer, count_per_query=args.count)

    output = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "query_count": len(queries),
        "job_count": len(jobs),
        "jobs": jobs,
    }

    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, ensure_ascii=False)

    print(f"Saved {len(jobs)} job posts → {args.output}")


if __name__ == "__main__":
    main()
