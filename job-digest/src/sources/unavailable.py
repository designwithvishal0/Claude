from __future__ import annotations

from .base import UnavailableSource

# Platforms this tool deliberately does not scrape, and why. Every one of
# these either has no free public job-search API, or only exposes listings
# behind logged-in / bot-protected surfaces where "scraping" means
# impersonating a browser to route around the platform's own ToS and
# anti-automation defenses. That trade isn't made here.
#
# Each also lists the legitimate path forward, for when/if it's wanted.

LINKEDIN = UnavailableSource(
    "linkedin",
    reason=(
        "No free public job-search API. LinkedIn's ToS prohibits automated "
        "scraping and it's actively enforced (rate limiting, account bans, "
        "litigation against scrapers). Legitimate options: LinkedIn Talent "
        "Solutions API (requires a partner agreement), or a personal saved-search "
        "email/RSS-style job alert configured manually in the LinkedIn UI."
    ),
)

NAUKRI = UnavailableSource(
    "naukri",
    reason=(
        "No public job-search API. Their listing pages sit behind active "
        "bot-detection; fetching them at scale would mean evading that "
        "protection, which this tool won't do. Legitimate option: Naukri's "
        "own job-alert emails, configured manually."
    ),
)

TWITTER = UnavailableSource(
    "twitter",
    reason=(
        "X/Twitter's job-relevant content (recruiter posts, #hiring threads) "
        "is only reachable at any real volume through the paid X API tiers "
        "(v2 search), and free scraping is against ToS and actively blocked. "
        "Wire in X_BEARER_TOKEN and implement src/sources/twitter.py against "
        "the official API if a paid tier is available."
    ),
)

WELLFOUND = UnavailableSource(
    "wellfound",
    reason=(
        "AngelList/Wellfound's public job-search API was retired; current "
        "listings require an authenticated session. No ToS-compliant "
        "automated path exists today. Legitimate option: Wellfound's own "
        "saved-search job alert emails, configured manually."
    ),
)

ALL = [LINKEDIN, NAUKRI, TWITTER, WELLFOUND]
