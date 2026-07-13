# Job scraper

Pulls jobs posted in the last 24 hours and writes them to `data/jobs-latest.json`
(and a dated snapshot under `data/history/`). Runs daily via
`.github/workflows/daily-job-scrape.yml`; view the results at `jobs.html` in
the repo root.

## Sources — what's included and why

| Source | Access method | Status |
|---|---|---|
| **Adzuna** | Free self-serve API (aggregates thousands of boards, incl. India) | Enabled — needs `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` |
| **RemoteOK** | Free, unauthenticated public JSON feed | Enabled by default |
| **X / Twitter** | Official API v2 recent-search | Optional — needs `TWITTER_BEARER_TOKEN`. As of 2026 the X API has no free tier (pay-per-read); only enable this if you're already paying for API access. |

## Sources deliberately *not* scraped

**LinkedIn, Naukri, and Wellfound (AngelList) are not scraped**, and this
project won't add direct HTML scrapers for them:

- **LinkedIn** has no public job-search API. Its "Jobs API" is a *posting* API
  gated behind an invitation-only Talent Solutions / ATS partnership — it lets
  approved enterprise platforms push job listings *to* LinkedIn, not query
  LinkedIn's listings. LinkedIn's User Agreement prohibits automated
  scraping and the company actively pursues legal/technical action against
  scrapers.
- **Naukri.com** has no official developer API for job search at all.
  Scraping its site would mean reverse-engineering an internal/private API in
  violation of its Terms of Service.
- **Wellfound** has no official API either; the same ToS concern applies.

If you have legitimate access to any of these (e.g. a LinkedIn Talent
Solutions partnership, or a Naukri recruiter data-feed agreement), add a
module under `src/sources/` following the same shape as `adzuna.mjs` — the
orchestrator in `src/index.mjs` will pick it up automatically as long as it
exports `name`, `isConfigured(env)`, and `fetchJobs({ env, queries, countries, maxAgeHours })`.

**Indeed** and **ZipRecruiter** are supported the same way: Indeed's old
Publisher API was deprecated in 2023 (its replacement is a sales-led
enterprise data deal), and ZipRecruiter's API requires a partner agreement.
Both are addressable with the same module pattern once you have credentials.

## Setup

1. Get a free Adzuna key at <https://developer.adzuna.com/> and add
   `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` as repo secrets (Settings → Secrets and
   variables → Actions).
2. Optionally set repo **variables** `JOB_QUERY` (comma-separated search
   terms, default covers common tech/PM/analyst roles) and `JOB_COUNTRIES`
   (comma-separated Adzuna country codes, default `us,gb,in,ca,au`).
3. The workflow runs daily at 06:17 UTC, or trigger it manually from the
   Actions tab (`workflow_dispatch`).
4. Locally: `cd job-scraper && node src/index.mjs` (Node 20+, no
   dependencies — uses the built-in `fetch`).

## Output shape

```json
{
  "generatedAt": "2026-07-13T06:17:00.000Z",
  "maxAgeHours": 24,
  "count": 42,
  "jobs": [
    {
      "id": "adzuna:123",
      "source": "Adzuna",
      "title": "Backend Engineer",
      "company": "Acme Inc",
      "location": "London, UK",
      "url": "https://...",
      "postedAt": "2026-07-13T02:00:00Z",
      "remote": false,
      "salary": "70000-90000",
      "description": "..."
    }
  ]
}
```

Jobs are deduped by URL (falling back to source+title+company) and filtered
to `postedAt` within the last `JOB_MAX_AGE_HOURS` (default 24).
