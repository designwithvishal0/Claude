"""
X (Twitter) Job Scraper
Searches X for job postings using configurable hashtags/keywords.
Outputs results to JSON and CSV.

Usage:
    python scrape_x_jobs.py
    python scrape_x_jobs.py --keywords "python developer" "remote engineer" --max 100
    python scrape_x_jobs.py --cookies cookies.json   # provide auth cookies for better results
"""

import asyncio
import json
import csv
import re
import argparse
from datetime import datetime
from pathlib import Path

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    raise SystemExit("playwright not installed. Run: pip install playwright && playwright install chromium")


# ── Config ──────────────────────────────────────────────────────────────────

DEFAULT_KEYWORDS = [
    "#hiring",
    "#jobopening",
    "#remotejobs",
    "#techjobs",
    "we are hiring",
]

JOB_SIGNAL_WORDS = [
    "hiring", "apply", "job", "role", "position", "opening", "opportunity",
    "join our team", "we're looking", "dm us", "link in bio", "salary",
    "full.?time", "part.?time", "remote", "onsite", "hybrid",
]

SCROLL_PAUSE_MS = 2000
SEARCH_WAIT_MS  = 4000


# ── Helpers ──────────────────────────────────────────────────────────────────

def looks_like_job(text: str) -> bool:
    pattern = "|".join(JOB_SIGNAL_WORDS)
    return bool(re.search(pattern, text, re.IGNORECASE))


def parse_post(raw: str, keyword: str, url: str) -> dict | None:
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if not lines or not looks_like_job(raw):
        return None

    # Very rough field extraction — good enough for a starting dataset
    title   = next((l for l in lines if any(w in l.lower() for w in ["engineer", "developer", "designer",
                    "manager", "analyst", "lead", "intern", "recruiter"])), "")
    company = next((l for l in lines if any(w in l.lower() for w in ["@", "inc", "ltd", "llc", "corp",
                    "studio", "labs", "team"])), "")

    return {
        "title":      title[:120],
        "company":    company[:80],
        "snippet":    raw[:400].replace("\n", " "),
        "keyword":    keyword,
        "post_url":   url,
        "scraped_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


# ── Core scraper ─────────────────────────────────────────────────────────────

async def load_cookies(page, cookie_file: str):
    path = Path(cookie_file)
    if not path.exists():
        print(f"  [warn] Cookie file '{cookie_file}' not found — continuing as guest.")
        return
    with path.open() as f:
        cookies = json.load(f)
    await page.context.add_cookies(cookies)
    print(f"  [info] Loaded {len(cookies)} cookies from {cookie_file}")


async def scrape_keyword(page, keyword: str, max_per_keyword: int) -> list[dict]:
    query = keyword.replace(" ", "%20").replace("#", "%23")
    url   = f"https://x.com/search?q={query}&f=live&src=typed_query"

    print(f"\n  Searching: {keyword}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(SEARCH_WAIT_MS)
    except PlaywrightTimeout:
        print(f"  [warn] Timed out loading search for '{keyword}'")
        return []

    # Check for login wall
    if await page.query_selector('[data-testid="loginButton"]'):
        print("  [warn] Login wall detected — guest results may be limited.")

    results: list[dict] = []
    seen: set[str] = set()
    scroll_attempts = 0
    max_scrolls = max(3, max_per_keyword // 10)

    while len(results) < max_per_keyword and scroll_attempts < max_scrolls:
        tweets = await page.query_selector_all('[data-testid="tweet"]')

        for tweet in tweets:
            try:
                text = await tweet.inner_text()
                # Try to grab the tweet's permalink
                link_el = await tweet.query_selector('a[href*="/status/"]')
                post_url = ""
                if link_el:
                    href = await link_el.get_attribute("href")
                    post_url = f"https://x.com{href}" if href and href.startswith("/") else href or ""

                key = post_url or text[:80]
                if key in seen:
                    continue
                seen.add(key)

                parsed = parse_post(text, keyword, post_url)
                if parsed:
                    results.append(parsed)
                    if len(results) >= max_per_keyword:
                        break
            except Exception:
                continue

        # Scroll to load more
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(SCROLL_PAUSE_MS)
        scroll_attempts += 1

    print(f"  Found {len(results)} job posts for '{keyword}'")
    return results


async def run(keywords: list[str], max_per_keyword: int, cookie_file: str | None, out_dir: Path):
    all_jobs: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        if cookie_file:
            await load_cookies(page, cookie_file)

        for kw in keywords:
            jobs = await scrape_keyword(page, kw, max_per_keyword)
            all_jobs.extend(jobs)

        await browser.close()

    # Deduplicate across keywords by snippet
    seen_snips: set[str] = set()
    unique: list[dict] = []
    for j in all_jobs:
        k = j["snippet"][:120]
        if k not in seen_snips:
            seen_snips.add(k)
            unique.append(j)

    return unique


# ── Output ───────────────────────────────────────────────────────────────────

def save_json(jobs: list[dict], path: Path):
    with path.open("w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"  JSON → {path}")


def save_csv(jobs: list[dict], path: Path):
    if not jobs:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
        writer.writeheader()
        writer.writerows(jobs)
    print(f"  CSV  → {path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Scrape job posts from X (Twitter)")
    p.add_argument("--keywords", nargs="+", default=DEFAULT_KEYWORDS,
                   help="Search keywords/hashtags (default: built-in list)")
    p.add_argument("--max", type=int, default=50,
                   help="Max job posts per keyword (default: 50)")
    p.add_argument("--cookies", type=str, default=None,
                   help="Path to cookies.json for authenticated session")
    p.add_argument("--out", type=str, default=".",
                   help="Output directory (default: current dir)")
    return p.parse_args()


async def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("X Job Scraper")
    print("=" * 40)
    print(f"Keywords : {args.keywords}")
    print(f"Max/kw   : {args.max}")
    print(f"Auth     : {args.cookies or 'guest (no cookies)'}")
    print(f"Output   : {out_dir.resolve()}")
    print("=" * 40)

    jobs = await run(
        keywords=args.keywords,
        max_per_keyword=args.max,
        cookie_file=args.cookies,
        out_dir=out_dir,
    )

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    save_json(jobs, out_dir / f"x_jobs_{ts}.json")
    save_csv(jobs,  out_dir / f"x_jobs_{ts}.csv")

    print(f"\nDone. {len(jobs)} unique job posts saved.")


if __name__ == "__main__":
    asyncio.run(main())
