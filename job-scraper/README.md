# Daily job digest

Pulls freshly-posted (last 24h) job listings once a day and writes them to
`data/latest.md` / `data/latest.json`, plus a dated snapshot for history. A
GitHub Actions workflow (`.github/workflows/daily-job-scrape.yml`) runs it
every day at 06:00 UTC and commits the results back to this repo.

## Run it yourself

```bash
cd job-scraper
pip install -r requirements.txt
python run.py
```

Edit `config.yaml` to change keywords, location, Adzuna country, and which
sources are enabled.

## Sources

| Source | Coverage | Auth |
|---|---|---|
| [RemoteOK](https://remoteok.com/api) | remote jobs, global | none — free public API |
| [Remotive](https://remotive.com/api-documentation) | remote jobs, global | none — free public API |
| [Arbeitnow](https://arbeitnow.com) | Germany/EU-focused, remote + onsite | none — free public API |
| [Adzuna](https://developer.adzuna.com/) | company career pages + boards, per-country (default: India) | free `app_id`/`app_key`, set as repo secrets `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` |
| [Jooble](https://jooble.org/api/about) | broad meta-search aggregator | free instant API key, set as repo secret `JOOBLE_API_KEY` |

The first three work out of the box with no signup. Adzuna and Jooble are
licensed aggregators — sign up for a free key and add it as a GitHub Actions
secret to turn them on; until then the run just logs them as skipped.

## Why LinkedIn, Naukri, Wellfound, and Twitter/X aren't scraped directly

Those platforms explicitly prohibit automated scraping in their Terms of
Service and run active anti-bot detection against it. Building a scraper
that logs in as a user, bypasses that detection, and pulls page data would
violate those terms — that's not something this tool does.

The legitimate way to get same-day postings from each of them:

- **LinkedIn** — turn on "Job Alerts" (daily or instant email) for your
  saved searches at linkedin.com/jobs — this is LinkedIn's own official
  notification feature. Programmatic access requires their partner-only
  Talent Solutions API.
- **Naukri** — same idea: "Job Alerts" under naukri.com/mnjuser/profile
  sends daily/instant email digests for saved searches. Naukri has no
  public API.
- **Wellfound** (AngelList Talent) — "Job Alerts" in your candidate
  preferences sends daily digests. Their API requires a partner
  application.
- **Twitter/X** — the current X API requires a paid tier for search access;
  without that, tracking `#hiring`-style posts isn't something this tool
  automates. If you have API access, `keywords`-based search could be added
  as another adapter.

If you want those postings folded into this same digest, the cleanest
compliant path is parsing the official alert emails from those platforms
(e.g. via the Gmail API) rather than scraping the sites — that's a natural
follow-up adapter but isn't wired up here since it needs your own mailbox
OAuth credentials.

## Output format

Each run writes:
- `data/<date>.json` / `data/latest.json` — structured job records
- `data/<date>.md` / `data/latest.md` — human-readable digest grouped by source

A job is kept only if its reported `posted_at` falls within `max_age_hours`
(default 24) of the run time. Postings with no parseable date are kept
rather than dropped, since staleness can't be proven either way.
