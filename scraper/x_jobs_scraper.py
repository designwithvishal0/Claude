#!/usr/bin/env python3
"""
X (Twitter) Job Scraper
Searches X for job postings using the v2 API and writes results to jobs_output.json.

Setup:
  1. Get a Bearer Token from developer.twitter.com (free Basic tier works)
  2. Set X_BEARER_TOKEN env var (or create a .env file)
  3. pip install -r requirements.txt
  4. python x_jobs_scraper.py

Without a token, the script generates demo data so the dashboard can be tested.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # python-dotenv is optional

BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN", "")
OUTPUT_PATH  = Path(__file__).parent / "jobs_output.json"

# Queries sent to the X v2 recent-search endpoint.
# Using -is:retweet keeps results clean; lang:en filters to English.
SEARCH_QUERIES = [
    "(we're hiring OR we are hiring) (engineer OR designer OR developer OR researcher) -is:retweet lang:en",
    "#hiring (remote OR hybrid OR onsite) (job OR role OR position) -is:retweet lang:en",
    "(senior OR staff OR lead OR principal) (engineer OR designer) hiring -is:retweet lang:en",
    "(VP OR head OR director) hiring (SaaS OR startup OR tech) -is:retweet lang:en",
]

# ── X API v2 ──────────────────────────────────────────────────────────────────

def _api_headers() -> dict:
    return {"Authorization": f"Bearer {BEARER_TOKEN}"}


def search_x(query: str, max_results: int = 25) -> list[dict]:
    """Call /2/tweets/search/recent and return normalised job dicts."""
    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        "query": query,
        "max_results": max(10, min(max_results, 100)),
        "tweet.fields": "created_at,author_id,text,entities",
        "expansions": "author_id",
        "user.fields": "name,username,verified",
    }
    resp = requests.get(url, headers=_api_headers(), params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
    jobs = []
    for tweet in data.get("data", []):
        author = users.get(tweet.get("author_id", ""), {})
        handle = author.get("username", "unknown")
        info   = _extract_info(tweet["text"])
        jobs.append({
            "id":           tweet["id"],
            "handle":       handle,
            "name":         author.get("name", handle),
            "verified":     author.get("verified", False),
            "text":         tweet["text"],
            "role":         info["role"],
            "location":     info["location"],
            "salary":       info["salary"],
            "remote":       info["remote"],
            "tags":         info["tags"],
            "postedAt":     tweet.get("created_at", ""),
            "tweetUrl":     f"https://x.com/{handle}/status/{tweet['id']}",
            "saved":        False,
            "source":       "X API v2",
        })
    return jobs


# ── Text parsing ──────────────────────────────────────────────────────────────

_SALARY_RE = re.compile(
    r'\$[\d,]+[kK]?\s*[-–—]\s*\$[\d,]+[kK]?'
    r'|\$[\d,]+[kK]?\+?'
    r'|[\d,]+[kK]\s*[-–—]\s*[\d,]+[kK]'
)
_ROLE_PATTERNS = [
    re.compile(r'(?:hiring|looking for|seeking)\s+(?:a\s+)?'
               r'((?:Senior|Staff|Principal|Lead|Junior|Mid-level|Head of|VP of)\s+[\w\s]+?'
               r'(?:Engineer|Developer|Designer|Manager|Researcher|Analyst|Scientist|Director|Lead))',
               re.I),
    re.compile(r'(?:Senior|Staff|Principal|Lead|Junior)\s+'
               r'[\w\s]{2,30}?(?:Engineer|Developer|Designer|Manager|Researcher)', re.I),
]
_TECH_TAGS = [
    'Python','TypeScript','JavaScript','Go','Rust','Swift','Kotlin',
    'React','Next.js','Vue','GraphQL','SQL','PostgreSQL',
    'AWS','GCP','Azure','Kubernetes','Docker',
    'ML','LLM','AI','Machine Learning','NLP','PyTorch','TensorFlow',
    'DevRel','Backend','Frontend','Full-Stack','iOS','Android','macOS',
    'Marketing','Growth','SEO','Demand Gen',
    'Enterprise Sales','Sales','B2B','SaaS',
    'Product Design','UX','UI',
    'Distributed Systems','Infrastructure','API',
]


def _extract_info(text: str) -> dict:
    info = {"role": None, "salary": None, "location": None, "remote": False, "tags": []}

    salary = _SALARY_RE.search(text)
    if salary:
        info["salary"] = salary.group(0)

    for pat in _ROLE_PATTERNS:
        m = pat.search(text)
        if m:
            info["role"] = m.group(0).strip()[:70]
            break

    lower = text.lower()
    if "remote" in lower:
        info["remote"] = True
        info["location"] = "Remote"
    elif "hybrid" in lower:
        info["location"] = "Hybrid"

    loc_m = re.search(r'\b(San Francisco|New York|NYC|London|Berlin|Austin|Seattle|Boston)\b', text, re.I)
    if loc_m and not info["location"]:
        info["location"] = loc_m.group(0)

    info["tags"] = [t for t in _TECH_TAGS if re.search(rf'\b{re.escape(t)}\b', text, re.I)][:6]
    return info


# ── Demo data (used when no API token is set) ─────────────────────────────────

def _demo_jobs() -> list[dict]:
    return [
        {
            "id": f"demo_{i}", "handle": h, "name": n, "verified": v,
            "text": txt, "role": role, "location": loc, "salary": sal,
            "remote": "remote" in loc.lower(), "tags": tags,
            "postedAt": pa, "tweetUrl": f"https://x.com/{h}", "saved": False,
            "source": "Demo",
        }
        for i, (h, n, v, txt, role, loc, sal, tags, pa) in enumerate([
            ("stripe","Stripe",True,
             "We're hiring a Senior Backend Engineer — Payments Infra team. Remote-friendly. $180k–$230k + equity.",
             "Senior Backend Engineer","Remote","$180k–$230k",["Go","Distributed Systems","API"],"2 h ago"),
            ("figma","Figma",True,
             "Join Figma as a Staff Product Designer 🎨 Hybrid SF/NYC. $200k–$260k + equity.",
             "Staff Product Designer","Hybrid · SF / NYC","$200k–$260k",["Product Design","Systems","Figma"],"5 h ago"),
            ("vercel","Vercel",True,
             "Hiring a DevRel Engineer — help devs build faster. 100% remote. Work with the Next.js team.",
             "Developer Relations Engineer","100% Remote","$140k–$170k",["React","Next.js","TypeScript","DevRel"],"7 h ago"),
            ("NotionHQ","Notion",True,
             "Notion is hiring a Senior ML Engineer ($220k–$280k, SF) for our AI team. 30M+ users.",
             "Senior ML Engineer","San Francisco, CA","$220k–$280k",["Python","LLMs","ML","AI"],"1 d ago"),
            ("supabase","Supabase",True,
             "Hiring Head of Marketing — lead demand gen + brand for fastest-growing open source startup. Fully remote.",
             "Head of Marketing","Fully Remote","$150k–$190k",["Marketing","Growth","B2B","SaaS"],"1 d ago"),
            ("AnthropicAI","Anthropic",True,
             "Anthropic is hiring across Safety Research, Infrastructure, and Product. SF-based, remote flex.",
             "Safety Researcher","San Francisco (Flexible)","$250k–$400k",["AI Safety","Research","Python","ML"],"2 d ago"),
        ])
    ]


# ── Main ──────────────────────────────────────────────────────────────────────

def main(max_per_query: int = 25):
    if not BEARER_TOKEN:
        print("No X_BEARER_TOKEN found — writing demo data to", OUTPUT_PATH)
        jobs = _demo_jobs()
    else:
        print(f"Searching X with {len(SEARCH_QUERIES)} queries...")
        jobs, seen = [], set()
        for q in SEARCH_QUERIES:
            print(f"  → {q[:60]}...")
            try:
                results = search_x(q, max_results=max_per_query)
                for j in results:
                    if j["id"] not in seen:
                        jobs.append(j)
                        seen.add(j["id"])
            except requests.HTTPError as e:
                print(f"  HTTP {e.response.status_code}: {e.response.text[:200]}")
            except Exception as e:
                print(f"  Error: {e}")
            time.sleep(2)  # stay within rate limits

    output = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "total":      len(jobs),
        "jobs":       jobs,
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\nDone — {len(jobs)} jobs saved to {OUTPUT_PATH}")
    return jobs


if __name__ == "__main__":
    main()
