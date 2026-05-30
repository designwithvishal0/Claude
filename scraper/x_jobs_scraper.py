#!/usr/bin/env python3
"""
X (Twitter) Job Scraper for Leadflow
Finds companies posting job openings on X and formats them as Leadflow leads.

Usage:
    python x_jobs_scraper.py --token YOUR_BEARER_TOKEN
    python x_jobs_scraper.py --token YOUR_BEARER_TOKEN --query "#hiring remote SaaS" --max 20
    python x_jobs_scraper.py --token YOUR_BEARER_TOKEN --out leads.json

Env var alternative:
    export X_BEARER_TOKEN=your_token
    python x_jobs_scraper.py

Get a bearer token at: https://developer.twitter.com/en/portal/dashboard
Free Basic tier supports recent tweet search (last 7 days).
"""

import os
import re
import json
import time
import argparse
import requests
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional


BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")

# Searches that surface companies actively hiring (= growth signal)
DEFAULT_QUERIES = [
    '(#hiring OR "we\'re hiring" OR "we are hiring") (#SaaS OR #startup OR #tech) -is:retweet lang:en',
    '("job opening" OR "open role" OR "join our team") (#engineering OR #product OR #growth OR #marketing) -is:retweet lang:en',
    '(#nowhiring OR #jobopening) (#remote OR #remotework) -is:retweet lang:en',
    '"looking for a" (engineer OR designer OR "product manager" OR "head of") to join -is:retweet lang:en',
]

# ICP signals — roles that indicate a company is scaling its go-to-market
GTM_ROLES = [
    "head of growth", "vp sales", "vp marketing", "demand gen", "revenue operations",
    "sales operations", "growth engineer", "growth manager", "marketing manager",
    "account executive", "sales development", "sdr", "bdr", "customer success",
    "product manager", "cro", "chief revenue", "director of sales",
]

SENIORITY_SIGNALS = ["vp", "head of", "director", "chief", "lead", "senior", "principal", "staff"]


@dataclass
class XJobLead:
    id: str
    name: str
    company: str
    title: str
    tweet_url: str
    tweet_text: str
    source: str = "X (Twitter)"
    score: int = 0
    temperature: str = "cold"
    roles_detected: list = field(default_factory=list)
    signals: list = field(default_factory=list)
    timestamp: str = ""


class XJobsScraper:

    API_BASE = "https://api.twitter.com/2"

    def __init__(self, bearer_token: str = ""):
        self.bearer = bearer_token or BEARER_TOKEN
        if not self.bearer:
            raise ValueError(
                "No bearer token found. Set X_BEARER_TOKEN env var or pass --token.\n"
                "Get one at: https://developer.twitter.com/en/portal/dashboard"
            )
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {self.bearer}"
        self.session.headers["User-Agent"] = "Leadflow-XScraper/1.0"

    def search_recent(self, query: str, max_results: int = 10) -> dict:
        resp = self.session.get(
            f"{self.API_BASE}/tweets/search/recent",
            params={
                "query": query,
                "max_results": max(10, min(max_results, 100)),
                "tweet.fields": "created_at,author_id,text,entities,public_metrics",
                "expansions": "author_id",
                "user.fields": "name,username,description,public_metrics,verified",
            },
            timeout=15,
        )
        if resp.status_code == 429:
            reset = int(resp.headers.get("x-rate-limit-reset", time.time() + 60))
            wait = max(1, reset - int(time.time()))
            print(f"  Rate limited — waiting {wait}s…")
            time.sleep(wait)
            return self.search_recent(query, max_results)
        resp.raise_for_status()
        return resp.json()

    def _detect_roles(self, text: str) -> list[str]:
        found = []
        lower = text.lower()
        for role in GTM_ROLES:
            if role in lower:
                found.append(role.title())
        return found

    def _infer_company(self, text: str, user_name: str, user_bio: str) -> str:
        patterns = [
            r"at\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s+we\s|\s+is\s|\s+are\s|[,!.\n])",
            r"([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)\s+is\s+(?:hiring|looking for)",
            r"join\s+(?:us\s+at\s+|the\s+team\s+at\s+)?([A-Z][A-Za-z0-9\s]+?)(?:\s+as\s+|\s+to\s+|[!.\n])",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                candidate = m.group(1).strip()
                if 2 <= len(candidate.split()) <= 4 and len(candidate) < 40:
                    return candidate
        return user_name  # fall back to poster's display name

    def _score(self, text: str, user: dict, roles: list) -> int:
        score = 40
        lower = text.lower()
        metrics = user.get("public_metrics", {})

        # Company growth signals
        if roles:
            score += min(20, len(roles) * 7)
        if any(r in lower for r in ["series a", "series b", "seed round", "raised", "funded"]):
            score += 15
        if "remote" in lower or "fully remote" in lower:
            score += 8
        if any(s in lower for s in SENIORITY_SIGNALS):
            score += 8

        # Engagement signals
        likes = metrics.get("like_count", 0)
        if likes > 100:
            score += 12
        elif likes > 20:
            score += 6

        followers = user.get("public_metrics", {}).get("followers_count", 0)
        if followers > 5000:
            score += 8
        elif followers > 1000:
            score += 4

        # ICP signals (GTM / B2B SaaS roles are most relevant)
        if any(r.lower() in lower for r in ["growth", "revenue", "sales", "marketing", "sdr", "bdr"]):
            score += 10

        return max(0, min(100, score))

    def _build_signals(self, text: str, user: dict, roles: list) -> list[dict]:
        metrics = user.get("public_metrics", {})
        lower = text.lower()
        signals = []

        if roles:
            signals.append({"label": "Roles detected", "value": ", ".join(roles[:2]), "tone": "good"})
        else:
            signals.append({"label": "Role type", "value": "General hire", "tone": "neutral"})

        if any(s in lower for s in SENIORITY_SIGNALS):
            signals.append({"label": "Seniority", "value": "Senior+", "tone": "good"})
        else:
            signals.append({"label": "Seniority", "value": "IC", "tone": "neutral"})

        likes = metrics.get("like_count", 0)
        signals.append({
            "label": "Post engagement",
            "value": f"{likes} likes",
            "tone": "good" if likes > 50 else "neutral",
        })

        growth_keyword = next(
            (k for k in ["Series A", "Series B", "seed", "funded", "remote"] if k.lower() in lower), None
        )
        if growth_keyword:
            signals.append({"label": "Growth signal", "value": growth_keyword, "tone": "good"})
        else:
            signals.append({"label": "Growth signal", "value": "None detected", "tone": "neutral"})

        return signals

    def parse_tweet(self, tweet: dict, users: dict) -> Optional[XJobLead]:
        text: str = tweet.get("text", "")
        author_id = tweet.get("author_id", "")
        user = users.get(author_id, {})

        username = user.get("username", "unknown")
        display_name = user.get("name", username)
        bio = user.get("description", "")

        roles = self._detect_roles(text)
        company = self._infer_company(text, display_name, bio)
        score = self._score(text, user, roles)
        temperature = "hot" if score >= 75 else "warm" if score >= 55 else "cold"

        title = "Hiring Manager"
        if any(s in display_name.lower() for s in ["vp", "cto", "ceo", "head", "founder", "director"]):
            title = display_name  # their X display name IS their title context
        elif bio:
            # pull first line of bio as title hint
            first_line = bio.split("\n")[0][:50]
            if first_line:
                title = first_line

        return XJobLead(
            id=tweet["id"],
            name=display_name,
            company=company,
            title=title,
            tweet_url=f"https://x.com/{username}/status/{tweet['id']}",
            tweet_text=text,
            score=score,
            temperature=temperature,
            roles_detected=roles,
            signals=self._build_signals(text, user, roles),
            timestamp=tweet.get("created_at", datetime.now(timezone.utc).isoformat()),
        )

    def scrape(self, queries: list[str] = None, max_per_query: int = 10) -> list[dict]:
        queries = queries or DEFAULT_QUERIES
        seen: dict[str, XJobLead] = {}

        for query in queries:
            print(f"\nSearching: {query[:70]}…")
            try:
                data = self.search_recent(query, max_per_query)
                tweets = data.get("data") or []
                users_list = (data.get("includes") or {}).get("users") or []
                users = {u["id"]: u for u in users_list}

                before = len(seen)
                for tweet in tweets:
                    if tweet["id"] not in seen:
                        lead = self.parse_tweet(tweet, users)
                        if lead:
                            seen[lead.id] = lead

                print(f"  Found {len(seen) - before} new leads (total: {len(seen)})")
                time.sleep(1.2)

            except requests.HTTPError as e:
                print(f"  HTTP {e.response.status_code} — {e.response.text[:200]}")
            except Exception as e:
                print(f"  Error: {e}")

        leads = sorted(seen.values(), key=lambda l: l.score, reverse=True)
        return [asdict(l) for l in leads]

    def to_leadflow_format(self, leads: list[dict]) -> list[dict]:
        """Convert scraped leads to Leadflow dashboard JSON schema."""
        result = []
        for i, l in enumerate(leads):
            first = l["name"].split()[0]
            initials = "".join(p[0].upper() for p in l["name"].split()[:2])
            result.append({
                "id": f"x{i+1}",
                "x_tweet_id": l["id"],
                "name": l["name"],
                "initials": initials,
                "title": l["title"],
                "company": l["company"],
                "email": f"@{l['tweet_url'].split('/')[3]}",
                "phone": l["tweet_url"],
                "location": "Remote / X",
                "source": "X (Twitter)",
                "owner": "Unassigned",
                "lastActivity": _relative_time(l["timestamp"]),
                "temp": l["temperature"],
                "score": l["score"],
                "insightWhy": l["temperature"],
                "summary": (
                    f"{l['company']} is actively hiring on X"
                    + (f" — roles detected: {', '.join(l['roles_detected'])}" if l["roles_detected"] else "")
                    + ". Companies posting jobs on X are scaling and are strong candidates for growth tooling."
                ),
                "signals": l["signals"],
                "suggested": [
                    {"title": "Reply to hiring thread", "desc": "Engage authentically on X"},
                    {"title": "Send cold DM", "desc": "Introduce Leadflow to the poster"},
                    {"title": "Find email via Hunter.io", "desc": "Move to email outreach"},
                ],
                "scoreReason": f"+{l['score']//4} fit · +{l['score']//3} intent · +{l['score']//5} engagement · +{l['score']//6} timing",
                "activity": [
                    {"t": _relative_time(l["timestamp"]), "type": "visit", "text": f"X hiring post detected: \"{l['tweet_text'][:120]}\""},
                    {"t": "Just now", "type": "ai", "text": f"AI scored this lead {l['score']}/100 — {l['temperature'].upper()} priority."},
                ],
                "tweet_url": l["tweet_url"],
                "tweet_text": l["tweet_text"],
            })
        return result


def _relative_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        s = int(delta.total_seconds())
        if s < 60:
            return f"{s}s ago"
        if s < 3600:
            return f"{s // 60}m ago"
        if s < 86400:
            return f"{s // 3600}h ago"
        return f"{s // 86400}d ago"
    except Exception:
        return "recently"


def main():
    parser = argparse.ArgumentParser(
        description="Scrape job postings from X and export as Leadflow leads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--token", help="X Bearer Token (or set X_BEARER_TOKEN)")
    parser.add_argument("--query", action="append", dest="queries", metavar="QUERY",
                        help="Custom search query (repeat for multiple). Defaults to built-in GTM queries.")
    parser.add_argument("--max", type=int, default=10, metavar="N",
                        help="Max results per query (default: 10, max: 100)")
    parser.add_argument("--out", default="x_jobs.json", metavar="FILE",
                        help="Output JSON file (default: x_jobs.json)")
    parser.add_argument("--leadflow", action="store_true",
                        help="Also write x_leads_leadflow.json in Leadflow dashboard format")
    args = parser.parse_args()

    scraper = XJobsScraper(bearer_token=args.token or "")
    leads = scraper.scrape(queries=args.queries, max_per_query=args.max)

    output = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "count": len(leads),
        "leads": leads,
    }
    with open(args.out, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved {len(leads)} raw leads → {args.out}")

    if args.leadflow:
        lf_leads = scraper.to_leadflow_format(leads)
        lf_out = args.out.replace(".json", "_leadflow.json")
        with open(lf_out, "w") as f:
            json.dump({"scraped_at": output["scraped_at"], "count": len(lf_leads), "leads": lf_leads}, f, indent=2)
        print(f"Saved {len(lf_leads)} Leadflow-format leads → {lf_out}")


if __name__ == "__main__":
    main()
