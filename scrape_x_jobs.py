"""
X (Twitter) Job Scraper
Searches X for job postings via Nitter (open-source X frontend) and direct X search.
Outputs lead-ready JSON compatible with the AI Lead Dashboard (index.html).

Usage:
    python scrape_x_jobs.py [--query "python developer"] [--limit 50] [--out jobs.json]

Dependencies:
    pip install requests beautifulsoup4 python-dateutil
"""

import argparse
import json
import logging
import re
import sys
import time
import random
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public Nitter instances (community-maintained, no auth needed)
# ---------------------------------------------------------------------------
NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.1d4.us",
    "https://nitter.kavin.rocks",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Hashtags / keywords that reliably surface hiring posts on X
DEFAULT_QUERIES = [
    "#hiring",
    "#jobs",
    "#jobalert",
    "#wearehiring",
    "#nowhiring",
    "#jobopening",
    "#recruiting",
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class JobLead:
    id: str
    title: str
    company: str
    location: str
    source: str = "X / Twitter"
    url: str = ""
    posted_at: str = ""
    description: str = ""
    contact: str = ""
    temperature: str = "warm"      # hot / warm / cold
    ai_score: int = 0
    ai_insight: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Nitter scraper
# ---------------------------------------------------------------------------
class NitterScraper:
    def __init__(self, instance: str, session: requests.Session):
        self.base = instance.rstrip("/")
        self.session = session

    def search(self, query: str, limit: int = 50) -> list[dict]:
        """Return raw tweet dicts from a Nitter search page."""
        tweets: list[dict] = []
        cursor = ""
        encoded_q = quote_plus(query)

        while len(tweets) < limit:
            url = f"{self.base}/search?f=tweets&q={encoded_q}"
            if cursor:
                url += f"&cursor={cursor}"

            try:
                r = self.session.get(url, headers=HEADERS, timeout=15)
                r.raise_for_status()
            except requests.RequestException as e:
                log.warning("Nitter fetch failed (%s): %s", self.base, e)
                break

            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.select(".timeline-item")
            if not items:
                break

            for item in items:
                tweet = _parse_nitter_item(item, self.base)
                if tweet:
                    tweets.append(tweet)
                if len(tweets) >= limit:
                    break

            # pagination cursor
            next_btn = soup.select_one(".show-more a")
            if next_btn and next_btn.get("href"):
                m = re.search(r"cursor=([^&]+)", next_btn["href"])
                cursor = m.group(1) if m else ""
            else:
                break

            time.sleep(random.uniform(1.0, 2.5))  # polite crawl delay

        return tweets


def _parse_nitter_item(item, base_url: str) -> Optional[dict]:
    """Extract relevant fields from a Nitter .timeline-item element."""
    content_el = item.select_one(".tweet-content")
    if not content_el:
        return None

    text = content_el.get_text(" ", strip=True)
    if not _is_job_post(text):
        return None

    # author / company
    name_el = item.select_one(".fullname")
    handle_el = item.select_one(".username")
    full_name = name_el.get_text(strip=True) if name_el else "Unknown"
    handle = handle_el.get_text(strip=True).lstrip("@") if handle_el else ""

    # timestamp
    date_el = item.select_one(".tweet-date a")
    posted_at = ""
    if date_el and date_el.get("title"):
        try:
            posted_at = dateparser.parse(date_el["title"]).isoformat()
        except Exception:
            posted_at = date_el.get_text(strip=True)

    # permalink
    link_el = item.select_one(".tweet-date a")
    tweet_url = ""
    if link_el and link_el.get("href"):
        tweet_url = urljoin(base_url, link_el["href"])

    # tweet id from URL
    tweet_id = re.search(r"/status/(\d+)", tweet_url)
    tweet_id = tweet_id.group(1) if tweet_id else f"{handle}-{random.randint(1000,9999)}"

    return {
        "id": tweet_id,
        "text": text,
        "author": full_name,
        "handle": handle,
        "posted_at": posted_at,
        "url": tweet_url,
    }


def _is_job_post(text: str) -> bool:
    """Heuristic filter — keep only tweets that look like job openings."""
    text_lower = text.lower()
    job_signals = [
        "hiring", "we're hiring", "job opening", "job opportunity",
        "apply now", "join our team", "open position", "looking for",
        "remote job", "full-time", "part-time", "job alert", "vacancy",
        "recruiter", "dm me", "send resume", "send cv",
    ]
    return any(sig in text_lower for sig in job_signals)


# ---------------------------------------------------------------------------
# Transform raw tweet → JobLead
# ---------------------------------------------------------------------------
_TITLE_PATTERNS = [
    # "Senior Python Developer", "Frontend Engineer", "Data Scientist"
    r"\b(Senior|Junior|Lead|Staff|Principal|Mid[\-\s]?level)?\s?"
    r"(Software|Frontend|Backend|Full[\-\s]?stack|Data|ML|AI|DevOps|Product|UX|UI|"
    r"Mobile|iOS|Android|Cloud|Security|QA|SRE|Platform|Analytics)\s?"
    r"(Engineer|Developer|Designer|Scientist|Analyst|Manager|Architect|Specialist|"
    r"Consultant|Lead|Director|VP|Head)\b",
    # "Hiring: XYZ"
    r"[Hh]iring[:\s]+([A-Z][a-zA-Z\s]{3,40})",
    # "Role: XYZ"
    r"\b[Rr]ole[:\s]+([A-Z][a-zA-Z\s]{3,40})",
]

_LOCATION_PATTERNS = [
    r"\b(Remote|Hybrid|On[\-\s]?site)\b",
    r"\b([A-Z][a-zA-Z]+(?:,\s?[A-Z]{2})?)\b(?=\s|$)",   # "New York, NY"
    r"📍\s*([A-Za-z ,]+)",
    r"Location[:\s]+([A-Za-z ,]+)",
]


def _extract_title(text: str) -> str:
    for pat in _TITLE_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(0).strip()[:80]
    # fallback: first ~60 chars before a newline/hashtag
    snippet = re.split(r"[\n#]", text)[0].strip()
    return snippet[:60] if snippet else "Job Opening"


def _extract_location(text: str) -> str:
    for pat in _LOCATION_PATTERNS:
        m = re.search(pat, text)
        if m:
            loc = (m.group(1) if m.lastindex else m.group(0)).strip()
            if 3 < len(loc) < 50:
                return loc
    return "Remote / Not specified"


def _score_lead(text: str) -> tuple[int, str, str]:
    """Return (score 0-100, temperature, ai_insight) for a job tweet."""
    score = 40  # baseline
    signals = []

    text_lower = text.lower()

    if "urgent" in text_lower or "immediate" in text_lower:
        score += 20
        signals.append("Urgent fill")
    if "remote" in text_lower:
        score += 10
        signals.append("Remote-friendly")
    if any(t in text_lower for t in ["senior", "lead", "staff", "principal"]):
        score += 10
        signals.append("Senior role")
    if any(t in text_lower for t in ["apply now", "dm me", "link in bio"]):
        score += 10
        signals.append("CTA present")
    if re.search(r"\$[\d,]+|\d+[kK]\s*(usd|per year|/yr|pa)", text_lower):
        score += 10
        signals.append("Salary listed")

    score = min(score, 99)

    if score >= 70:
        temp = "hot"
    elif score >= 50:
        temp = "warm"
    else:
        temp = "cold"

    insight = "Job post from X. " + ("; ".join(signals) if signals else "Standard listing.")
    return score, temp, insight


def tweet_to_lead(raw: dict) -> JobLead:
    text = raw["text"]
    title = _extract_title(text)
    location = _extract_location(text)
    score, temp, insight = _score_lead(text)

    # extract hashtags as tags
    tags = re.findall(r"#(\w+)", text)[:6]

    # contact = handle mention or "apply" URL in tweet
    contact_match = re.search(r"@(\w+)", text)
    contact = f"@{contact_match.group(1)}" if contact_match else f"@{raw['handle']}"

    return JobLead(
        id=f"x-{raw['id']}",
        title=title,
        company=raw["author"],
        location=location,
        url=raw["url"],
        posted_at=raw["posted_at"],
        description=text[:300],
        contact=contact,
        temperature=temp,
        ai_score=score,
        ai_insight=insight,
        tags=tags,
    )


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------
def scrape(queries: list[str], limit_per_query: int = 50) -> list[JobLead]:
    session = requests.Session()
    session.headers.update(HEADERS)

    all_leads: list[JobLead] = []
    seen_ids: set[str] = set()

    # pick a working Nitter instance
    nitter = _pick_nitter_instance(session)
    if nitter is None:
        log.error("No Nitter instance available. Check connectivity or try again later.")
        return []

    log.info("Using Nitter instance: %s", nitter.base)

    for query in queries:
        log.info("Searching: %s", query)
        raw_tweets = nitter.search(query, limit=limit_per_query)
        log.info("  → %d candidate tweets", len(raw_tweets))

        for raw in raw_tweets:
            if raw["id"] in seen_ids:
                continue
            seen_ids.add(raw["id"])
            lead = tweet_to_lead(raw)
            all_leads.append(lead)

        time.sleep(random.uniform(2, 4))

    # sort by AI score descending
    all_leads.sort(key=lambda l: l.ai_score, reverse=True)
    return all_leads


def _pick_nitter_instance(session: requests.Session) -> Optional[NitterScraper]:
    for url in NITTER_INSTANCES:
        try:
            r = session.get(f"{url}/search?q=test", headers=HEADERS, timeout=10)
            if r.status_code == 200:
                return NitterScraper(url, session)
        except requests.RequestException:
            continue
    return None


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Scrape job postings from X via Nitter")
    ap.add_argument("--query", "-q", nargs="*", help="Search query/hashtag(s)")
    ap.add_argument("--limit", "-l", type=int, default=50,
                    help="Max tweets per query (default 50)")
    ap.add_argument("--out", "-o", default="x_jobs.json",
                    help="Output JSON file (default: x_jobs.json)")
    args = ap.parse_args()

    queries = args.query if args.query else DEFAULT_QUERIES

    log.info("Starting X job scrape — %d queries, limit %d each", len(queries), args.limit)
    leads = scrape(queries, limit_per_query=args.limit)

    output = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source": "X / Twitter",
        "total": len(leads),
        "leads": [l.to_dict() for l in leads],
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    log.info("Saved %d job leads → %s", len(leads), args.out)

    # quick preview
    if leads:
        print("\n--- Top 5 job leads ---")
        for lead in leads[:5]:
            print(f"  [{lead.ai_score:>3}] {lead.title} @ {lead.company}  ({lead.location})")
            print(f"        {lead.url}")


if __name__ == "__main__":
    main()
