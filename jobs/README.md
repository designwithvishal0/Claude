# Daily job digest

This folder is a running log from a scheduled task: "scrape jobs daily across
platforms (Twitter, Indeed, Naukri, LinkedIn, Wellfound, etc.), filtered to
postings from the last 24 hours." One dated file (`YYYY-MM-DD.md`) is added
per run.

## What actually runs, and why it's narrower than "all platforms"

Only two sources are wired up: **Indeed** and **ZipRecruiter**, via the job
search tools available in this environment. The others named in the request
are intentionally not scraped:

- **LinkedIn** — ToS explicitly prohibits automated scraping/bots against the
  site. Jobs data is only available through a LinkedIn Talent/Jobs API
  partnership.
- **Naukri** — same story: no public search API, and their terms bar
  automated data collection. Would need an employer/partner API agreement.
- **Twitter/X** — job posts there are informal (recruiter tweets), not a
  structured feed. Reading them at any volume requires the paid X API v2
  search endpoint, which isn't configured here.
- **Wellfound (AngelList Talent)** — has no public jobs API; listings would
  require manual browsing or a data-partner agreement.

If/when credentials or a compliant partner feed for any of these become
available, add a fetch step for that source into the daily run — the format
below (one markdown file per day, role/company/location/date/link) is meant
to stay the same regardless of source.

## Search scope assumed

No specific role, location, or seniority was given, so each run searches:

- `UI/UX Designer` and `Product Designer`
- Locations: India and Remote/US

Edit this file (or hand the runner new terms) to change what's searched.

## Freshness caveat

"Last 24 hours" is enforced where the source supports it (ZipRecruiter's
`max_posted_minutes_ago`). Indeed's tool has no freshness filter, so results
are filtered by eye against each listing's posted date, and Indeed date
fields have shown demo/placeholder timestamps ahead of the real calendar —
treat exact "posted N hours ago" claims from Indeed as approximate.
