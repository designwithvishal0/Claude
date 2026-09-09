# Job digest

A daily job-posting aggregator. Fetches postings from a handful of
sources, keeps only what was posted in the last 24 hours (configurable),
filters by your keywords, and writes a digest to `digests/`.

## Quickstart

```bash
cd job-digest
pip install -r requirements.txt
python3 main.py
```

Output goes to `digests/YYYY-MM-DD.md`, `digests/YYYY-MM-DD.json`, and
`digests/latest.md`.

Edit `config.yaml` to set your `keywords`, `locations`, and
`freshness_hours`. Keyword matching is substring, case-insensitive, against
the posting title — e.g. `"product designer"` matches "Senior Product
Designer, AI".

## What it actually scrapes, and what it doesn't

This aggregator only pulls from sources with a **free, public, documented**
API or feed — no logging in, no impersonating a browser to route around
anti-bot defenses.

**Enabled by default** (real, working, no API key needed):
- **RemoteOK** — public JSON API (`remoteok.com/api`)
- **We Work Remotely** — public per-category RSS feeds
- **Hacker News "Who is hiring?"** — via the public HN Algolia API

**Off by default, need your own credentials** (`src/sources/indeed.py`,
`src/sources/ziprecruiter.py`): Indeed and ZipRecruiter both retired their
old open/keyless consumer APIs. Job search access now goes through each
platform's partner program. This repo can't hand you those credentials —
get them yourself, set the relevant env var
(`INDEED_PARTNER_API_KEY` / `ZIPRECRUITER_API_KEY`), fill in the
`fetch()` method against the endpoint your agreement gives you, and add
the source name to `enabled_sources` in `config.yaml`.

**Deliberately not scraped at all** (`src/sources/unavailable.py` has the
full reasoning per platform):
- **LinkedIn** — no free job-search API; ToS explicitly bars scraping and
  it's actively enforced. Use LinkedIn Talent Solutions (partner
  agreement) or a manual saved-search job alert instead.
- **Naukri** — no public API; listings sit behind active bot-detection.
  Use Naukri's own job-alert emails instead.
- **X/Twitter** — meaningful coverage needs the paid X API v2 search tier;
  free scraping is against ToS and blocked. Wire up `X_BEARER_TOKEN` and
  implement `src/sources/twitter.py` if you have paid access.
- **Wellfound** — its public job-search API was retired; current listings
  require an authenticated session. Use Wellfound's saved-search alerts
  instead.

The point isn't laziness — it's that reliably pulling fresh listings from
those platforms without a partner API means writing code to impersonate a
browser and evade the anti-automation systems they actively maintain
against exactly this. That's a different (and much riskier) thing to
build than "call a documented API," and this project doesn't do it.

## Daily automation

`.github/workflows/daily-job-digest.yml` runs `main.py` every day and
commits the new digest file to `job-digest/digests/`. It needs no secrets
for the default sources. If you enable Indeed or ZipRecruiter, add their
API keys as repository secrets and reference them in the workflow's `env:`.

## Extending

Add a new source by subclassing `JobSource` in `src/sources/` (see
`remoteok.py` for the simplest example), registering it in
`src/aggregator.py`'s `_load_registry()`, and adding its name to
`enabled_sources` in `config.yaml`.
