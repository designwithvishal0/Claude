#!/usr/bin/env python3
"""
X (Twitter) Job Scraper
========================
Scrapes job postings from X using authenticated API access.

─── Setup (choose one method) ───────────────────────────────────────────────

  Method A – X Developer API v2  (most reliable, official)
  ─────────────────────────────
  1. Create a free account at https://developer.x.com
  2. Create an App → copy the Bearer Token
  3. Run:
       python scrape_x_jobs.py --bearer YOUR_BEARER_TOKEN

  Method B – Browser cookies  (no developer account needed)
  ──────────────────────────
  1. Log in to https://x.com in your browser
  2. Open DevTools (F12) → Application → Cookies → https://x.com
  3. Copy the values of  auth_token  and  ct0
  4. Run:
       python scrape_x_jobs.py --auth-token TOKEN --ct0 CT0_VALUE
     Or save them to a .env file and the script will pick them up.

─── Usage ───────────────────────────────────────────────────────────────────

  # Broad hiring search (default queries)
  python scrape_x_jobs.py --bearer $X_BEARER_TOKEN

  # Custom query
  python scrape_x_jobs.py "product manager remote 2025" --bearer $X_BEARER_TOKEN

  # Cookie auth
  python scrape_x_jobs.py --auth-token abc123 --ct0 def456

  # 5 pages, CSV output
  python scrape_x_jobs.py --pages 5 --output jobs.csv --bearer $X_BEARER_TOKEN

  # Pretty JSON to stdout
  python scrape_x_jobs.py --pretty --output - --bearer $X_BEARER_TOKEN

─── Output fields ───────────────────────────────────────────────────────────

  id, text, company, handle, followers, verified,
  posted_at, url, apply_links, links, retweets, likes, replies
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
from typing import Optional

import requests

# ─── Constants ────────────────────────────────────────────────────────────────

# X's public web-app bearer token (embedded in their JS — not a secret)
_GUEST_BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D"
    "1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

_API = "https://api.twitter.com"
_X   = "https://x.com"

# GraphQL features payload (required by the web app)
_GQL_FEATURES = {
    "rweb_lists_timeline_redesign_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": False,
    "interactive_text_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
    "blue_business_profile_image_shape_enabled": True,
}

# Default queries targeting job-posting accounts on X
DEFAULT_QUERIES = [
    "we're hiring (engineer OR developer OR designer) -is:retweet lang:en",
    "now hiring (remote OR hybrid OR \"full-time\") -is:retweet lang:en",
    "job opening (apply OR careers OR \"job link\") -is:retweet lang:en",
]

# URL keywords that suggest a job application link
_JOB_LINK_KEYWORDS = (
    "job", "career", "lever.co", "greenhouse.io", "workable.com",
    "ashbyhq.com", "recruit", "apply", "hire", "talent", "breezy",
    "smartrecruiters", "bamboohr", "workday", "jobs.",
)


# ─── Session builders ─────────────────────────────────────────────────────────

def _base_headers() -> dict:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": _X,
        "Referer": f"{_X}/",
        "x-twitter-client-language": "en",
        "x-twitter-active-user": "yes",
    }


def build_v2_session(bearer: str) -> requests.Session:
    """Session for X API v2 (developer Bearer Token)."""
    s = requests.Session()
    s.headers.update(_base_headers())
    s.headers["Authorization"] = f"Bearer {bearer}"
    return s


def build_cookie_session(auth_token: str, ct0: str) -> requests.Session:
    """Session authenticated via browser cookies (auth_token + ct0)."""
    s = requests.Session()
    s.headers.update(_base_headers())
    s.headers["Authorization"] = f"Bearer {_GUEST_BEARER}"
    s.headers["x-csrf-token"] = ct0
    s.cookies.set("auth_token", auth_token, domain=".x.com")
    s.cookies.set("ct0",        ct0,        domain=".x.com")
    return s


# ─── Query-ID discovery ───────────────────────────────────────────────────────

def _discover_search_query_id() -> Optional[str]:
    """Fetch X's main JS bundle and extract the current SearchTimeline query ID."""
    try:
        page = requests.get(_X, timeout=10,
                            headers={"User-Agent": _base_headers()["User-Agent"]})
        bundle_url = re.search(
            r'https://abs\.twimg\.com/responsive-web/client-web/main\.[a-f0-9]+\.js',
            page.text,
        )
        if not bundle_url:
            return None

        js = requests.get(bundle_url.group(), timeout=30,
                          headers={"User-Agent": _base_headers()["User-Agent"]})
        match = re.search(r'queryId:"([^"]+)",operationName:"SearchTimeline"', js.text)
        if match:
            qid = match.group(1)
            _info(f"Discovered SearchTimeline query ID: {qid}")
            return qid
    except Exception as exc:
        _warn(f"Query ID discovery failed: {exc}")
    return None


# ─── Search implementations ───────────────────────────────────────────────────

def _v2_search(
    session: requests.Session,
    query: str,
    next_token: Optional[str] = None,
    max_results: int = 100,
) -> Optional[dict]:
    """X API v2 recent-tweet search (requires developer bearer token)."""
    params: dict = {
        "query": query,
        "max_results": min(max_results, 100),
        "tweet.fields": "created_at,author_id,public_metrics,entities,lang",
        "expansions": "author_id",
        "user.fields": "name,username,public_metrics,verified,entities",
    }
    if next_token:
        params["next_token"] = next_token

    try:
        r = session.get(
            f"{_API}/2/tweets/search/recent",
            params=params,
            timeout=20,
        )
        if r.status_code == 200:
            return r.json()
        _warn(f"v2 search HTTP {r.status_code}: {r.text[:200]}")
    except requests.RequestException as exc:
        _warn(f"v2 search error: {exc}")
    return None


def _gql_search(
    session: requests.Session,
    query: str,
    query_id: str,
    cursor: Optional[str] = None,
    count: int = 20,
    product: str = "Latest",
) -> Optional[dict]:
    """X internal GraphQL SearchTimeline (requires cookie auth or developer token)."""
    variables: dict = {
        "rawQuery": query,
        "count": count,
        "querySource": "typed_query",
        "product": product,
    }
    if cursor:
        variables["cursor"] = cursor

    params = {
        "variables": json.dumps(variables, separators=(",", ":")),
        "features": json.dumps(_GQL_FEATURES, separators=(",", ":")),
    }

    url = f"{_API}/graphql/{query_id}/SearchTimeline"
    try:
        r = session.get(url, params=params, timeout=20)
        if r.status_code == 200:
            return r.json()
        _warn(f"GraphQL search HTTP {r.status_code}: {r.text[:200]}")
    except requests.RequestException as exc:
        _warn(f"GraphQL search error: {exc}")
    return None


# ─── Response parsers ─────────────────────────────────────────────────────────

def _parse_v2_response(data: dict) -> tuple[list[dict], Optional[str]]:
    """Parse X API v2 response into (job_dicts, next_token)."""
    tweets = data.get("data", [])
    users  = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
    next_token = data.get("meta", {}).get("next_token")

    results = []
    for t in tweets:
        author = users.get(t.get("author_id", ""), {})
        entities = t.get("entities", {})
        urls = [
            u.get("expanded_url", "")
            for u in entities.get("urls", [])
            if u.get("expanded_url") and "t.co" not in u.get("expanded_url", "")
        ]
        metrics = t.get("public_metrics", {})
        screen_name = author.get("username", "")
        tid = t.get("id", "")
        results.append({
            "id":          tid,
            "text":        t.get("text", ""),
            "company":     author.get("name", ""),
            "handle":      f"@{screen_name}",
            "followers":   author.get("public_metrics", {}).get("followers_count", 0),
            "verified":    author.get("verified", False),
            "posted_at":   t.get("created_at", ""),
            "url":         f"https://x.com/{screen_name}/status/{tid}",
            "apply_links": [l for l in urls if any(k in l.lower() for k in _JOB_LINK_KEYWORDS)],
            "links":       urls,
            "retweets":    metrics.get("retweet_count", 0),
            "likes":       metrics.get("like_count", 0),
            "replies":     metrics.get("reply_count", 0),
        })

    return results, next_token


def _parse_gql_response(data: dict) -> tuple[list[dict], Optional[str]]:
    """Parse GraphQL SearchTimeline response into (job_dicts, next_cursor)."""
    results: list[dict] = []
    next_cursor: Optional[str] = None

    try:
        instructions = (
            data.get("data", {})
            .get("search_by_raw_query", {})
            .get("search_timeline", {})
            .get("timeline", {})
            .get("instructions", [])
        )
        for inst in instructions:
            if inst.get("type") != "TimelineAddEntries":
                continue
            for entry in inst.get("entries", []):
                content = entry.get("content", {})
                etype   = content.get("entryType", "")

                if etype == "TimelineTimelineCursor":
                    if content.get("cursorType") == "Bottom":
                        next_cursor = content.get("value")
                    continue

                raw_tweet = (
                    content.get("itemContent", {})
                    .get("tweet_results", {})
                    .get("result", {})
                )
                if raw_tweet.get("__typename") == "Tweet":
                    job = _parse_gql_tweet(raw_tweet)
                    if job:
                        results.append(job)

                for item in content.get("items", []):
                    r2 = (
                        item.get("item", {})
                        .get("itemContent", {})
                        .get("tweet_results", {})
                        .get("result", {})
                    )
                    if r2.get("__typename") == "Tweet":
                        job = _parse_gql_tweet(r2)
                        if job:
                            results.append(job)
    except Exception as exc:
        _warn(f"GQL parse error: {exc}")

    return results, next_cursor


def _parse_gql_tweet(raw: dict) -> Optional[dict]:
    try:
        user_legacy  = (
            raw.get("core", {})
            .get("user_results", {})
            .get("result", {})
            .get("legacy", {})
        )
        is_blue = bool(
            raw.get("core", {})
            .get("user_results", {})
            .get("result", {})
            .get("is_blue_verified")
        )
        tweet = raw.get("legacy", {})
        tid   = tweet.get("id_str", "")
        screen_name = user_legacy.get("screen_name", "")

        urls = [
            u.get("expanded_url", "")
            for u in tweet.get("entities", {}).get("urls", [])
            if u.get("expanded_url") and "t.co" not in u.get("expanded_url", "")
        ]

        return {
            "id":          tid,
            "text":        tweet.get("full_text", ""),
            "company":     user_legacy.get("name", ""),
            "handle":      f"@{screen_name}",
            "followers":   user_legacy.get("followers_count", 0),
            "verified":    user_legacy.get("verified", False) or is_blue,
            "posted_at":   tweet.get("created_at", ""),
            "url":         f"https://x.com/{screen_name}/status/{tid}",
            "apply_links": [l for l in urls if any(k in l.lower() for k in _JOB_LINK_KEYWORDS)],
            "links":       urls,
            "retweets":    tweet.get("retweet_count", 0),
            "likes":       tweet.get("favorite_count", 0),
            "replies":     tweet.get("reply_count", 0),
        }
    except Exception as exc:
        _warn(f"Tweet parse error: {exc}")
        return None


# ─── Main scrape routines ─────────────────────────────────────────────────────

def scrape_via_v2_api(
    bearer: str,
    query: str,
    pages: int = 3,
    delay: float = 2.0,
) -> list[dict]:
    """Scrape using X API v2 (requires developer Bearer Token)."""
    session = build_v2_session(bearer)
    results: list[dict] = []
    seen: set[str] = set()
    next_token: Optional[str] = None

    for page in range(1, pages + 1):
        _info(f"[v2] Page {page}/{pages}")
        data = _v2_search(session, query, next_token=next_token)
        if not data:
            break

        jobs, next_token = _parse_v2_response(data)
        for j in jobs:
            if j["id"] not in seen:
                seen.add(j["id"])
                results.append(j)

        _info(f"  → {len(jobs)} tweets  (total: {len(results)})")

        if not next_token:
            _info("  Reached last page.")
            break
        if page < pages:
            time.sleep(delay)

    return results


def scrape_via_cookie_auth(
    auth_token: str,
    ct0: str,
    query: str,
    pages: int = 3,
    delay: float = 2.0,
    product: str = "Latest",
) -> list[dict]:
    """Scrape using browser cookie authentication."""
    session  = build_cookie_session(auth_token, ct0)
    query_id = _discover_search_query_id()
    if not query_id:
        _warn("Could not discover SearchTimeline query ID — cannot continue.")
        return []

    results: list[dict] = []
    seen: set[str] = set()
    cursor: Optional[str] = None

    for page in range(1, pages + 1):
        _info(f"[cookie] Page {page}/{pages}")
        data = _gql_search(session, query, query_id, cursor=cursor, product=product)
        if not data:
            break

        jobs, cursor = _parse_gql_response(data)
        for j in jobs:
            if j["id"] not in seen:
                seen.add(j["id"])
                results.append(j)

        _info(f"  → {len(jobs)} tweets  (total: {len(results)})")

        if not cursor:
            _info("  Reached last page.")
            break
        if page < pages:
            time.sleep(delay)

    return results


def scrape_jobs(
    query: str,
    *,
    bearer: Optional[str] = None,
    auth_token: Optional[str] = None,
    ct0: Optional[str] = None,
    pages: int = 3,
    delay: float = 2.0,
    product: str = "Latest",
) -> list[dict]:
    """
    Scrape job posts from X.  Pass exactly one of:
      • bearer    — developer Bearer Token (X API v2)
      • auth_token + ct0 — browser cookies from a logged-in X session
    """
    if bearer:
        return scrape_via_v2_api(bearer, query, pages=pages, delay=delay)
    if auth_token and ct0:
        return scrape_via_cookie_auth(
            auth_token, ct0, query,
            pages=pages, delay=delay, product=product,
        )
    raise ValueError(
        "Provide --bearer OR (--auth-token AND --ct0).  "
        "See the module docstring for setup instructions."
    )


def scrape_multiple(queries: list[str], **kwargs) -> list[dict]:
    """Run scrape_jobs for each query and merge, deduplicating by tweet ID."""
    seen: set[str] = set()
    all_results: list[dict] = []
    delay = kwargs.get("delay", 2.0)

    for i, q in enumerate(queries):
        _info(f"\n── Query {i + 1}/{len(queries)}: {q!r}")
        try:
            jobs = scrape_jobs(q, **kwargs)
        except ValueError as exc:
            _fatal(str(exc))
        for j in jobs:
            if j["id"] not in seen:
                seen.add(j["id"])
                all_results.append(j)
        if i < len(queries) - 1:
            time.sleep(delay * 2)

    return all_results


# ─── Output ───────────────────────────────────────────────────────────────────

def to_csv(jobs: list[dict]) -> str:
    if not jobs:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(jobs[0].keys()), extrasaction="ignore")
    writer.writeheader()
    for job in jobs:
        row = {k: "|".join(v) if isinstance(v, list) else v for k, v in job.items()}
        writer.writerow(row)
    return buf.getvalue()


def write_output(content: str, path: str) -> None:
    if path == "-":
        print(content)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        _info(f"Saved → {path}")


# ─── Logging ──────────────────────────────────────────────────────────────────

def _info(msg: str) -> None:
    print(f"[info] {msg}", file=sys.stderr)

def _warn(msg: str) -> None:
    print(f"[warn] {msg}", file=sys.stderr)

def _fatal(msg: str) -> None:
    print(f"[error] {msg}", file=sys.stderr)
    sys.exit(1)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scrape_x_jobs",
        description="Scrape job postings from X (Twitter)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    p.add_argument(
        "query", nargs="?", default=None,
        help="X search query. Omit to run the three built-in job-hunting queries.",
    )

    auth = p.add_argument_group("Authentication (required — pick one method)")
    auth.add_argument(
        "--bearer", metavar="TOKEN", default=os.getenv("X_BEARER_TOKEN"),
        help="X API v2 Bearer Token. Env: X_BEARER_TOKEN",
    )
    auth.add_argument(
        "--auth-token", metavar="TOKEN", default=os.getenv("X_AUTH_TOKEN"),
        help="Browser cookie 'auth_token'. Env: X_AUTH_TOKEN",
    )
    auth.add_argument(
        "--ct0", metavar="TOKEN", default=os.getenv("X_CT0"),
        help="Browser cookie 'ct0' (CSRF token). Env: X_CT0",
    )

    opts = p.add_argument_group("Scraping options")
    opts.add_argument(
        "--pages", type=int, default=3, metavar="N",
        help="Pages to fetch per query (default: 3, ~20–100 posts each).",
    )
    opts.add_argument(
        "--delay", type=float, default=2.0, metavar="SEC",
        help="Seconds between page requests (default: 2.0).",
    )
    opts.add_argument(
        "--product", choices=["Latest", "Top"], default="Latest",
        help="Result ordering for cookie-auth mode (default: Latest).",
    )

    out = p.add_argument_group("Output")
    out.add_argument(
        "--output", default="jobs.json", metavar="FILE",
        help="Output file. Use '-' for stdout. Extension sets format: .json or .csv (default: jobs.json).",
    )
    out.add_argument(
        "--pretty", action="store_true",
        help="Pretty-print JSON (ignored for CSV).",
    )

    return p


def main(argv=None) -> int:
    args = _parser().parse_args(argv)

    # Validate auth
    has_bearer = bool(args.bearer)
    has_cookie = bool(args.auth_token and args.ct0)

    if not has_bearer and not has_cookie:
        _fatal(
            "No credentials provided.\n\n"
            "  Method A (X API v2):\n"
            "    python scrape_x_jobs.py --bearer YOUR_BEARER_TOKEN\n"
            "    (get one free at https://developer.x.com)\n\n"
            "  Method B (browser cookies):\n"
            "    python scrape_x_jobs.py --auth-token TOKEN --ct0 CT0_VALUE\n"
            "    (copy from DevTools → Application → Cookies → x.com)\n\n"
            "  You can also set env vars: X_BEARER_TOKEN, X_AUTH_TOKEN, X_CT0"
        )

    kwargs = dict(
        bearer=args.bearer if has_bearer else None,
        auth_token=args.auth_token if has_cookie else None,
        ct0=args.ct0 if has_cookie else None,
        pages=args.pages,
        delay=args.delay,
        product=args.product,
    )

    queries = [args.query] if args.query else DEFAULT_QUERIES
    _info(f"Auth mode: {'v2 API' if has_bearer else 'cookie'}")
    _info(f"Queries: {len(queries)}")

    jobs = (
        scrape_jobs(queries[0], **kwargs)
        if len(queries) == 1
        else scrape_multiple(queries, **kwargs)
    )

    if not jobs:
        _warn("No jobs collected.")
        return 1

    fmt = "csv" if args.output.endswith(".csv") else "json"
    content = (
        to_csv(jobs) if fmt == "csv"
        else json.dumps(jobs, indent=2 if args.pretty else None, ensure_ascii=False)
    )

    write_output(content, args.output)
    print(f"\n✓  {len(jobs)} job posts  →  {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
