from __future__ import annotations

import logging
from datetime import datetime, timezone

from .models import JobPosting
from .sources.base import JobSource

logger = logging.getLogger(__name__)

SOURCE_REGISTRY: dict[str, type[JobSource]] = {}


def register(name: str, source_cls: type[JobSource]) -> None:
    SOURCE_REGISTRY[name] = source_cls


def _load_registry() -> None:
    from .sources.hn_hiring import HNWhoIsHiringSource
    from .sources.indeed import IndeedSource
    from .sources.remoteok import RemoteOKSource
    from .sources.weworkremotely import WeWorkRemotelySource
    from .sources.ziprecruiter import ZipRecruiterSource

    register("remoteok", RemoteOKSource)
    register("weworkremotely", WeWorkRemotelySource)
    register("hn_hiring", HNWhoIsHiringSource)
    register("indeed", IndeedSource)
    register("ziprecruiter", ZipRecruiterSource)


_load_registry()


def collect(enabled_sources: list[str]) -> list[JobPosting]:
    """Fetch postings from every enabled source. A single source failing
    (network error, schema change) is logged and skipped rather than
    aborting the whole run."""
    postings: list[JobPosting] = []
    for name in enabled_sources:
        source_cls = SOURCE_REGISTRY.get(name)
        if source_cls is None:
            logger.warning("Unknown source %r in enabled_sources, skipping", name)
            continue
        try:
            fetched = source_cls().fetch()
            logger.info("%s: fetched %d postings", name, len(fetched))
            postings.extend(fetched)
        except Exception:
            logger.exception("%s: failed to fetch, skipping", name)
    return postings


def matches_keywords(posting: JobPosting, keywords: list[str]) -> bool:
    if not keywords:
        return True
    title = posting.title.lower()
    return any(kw.lower() in title for kw in keywords)


def matches_locations(posting: JobPosting, locations: list[str]) -> bool:
    if not locations:
        return True
    location = posting.location.lower()
    return any(loc.lower() in location for loc in locations) or not posting.location


def filter_postings(
    postings: list[JobPosting],
    keywords: list[str],
    locations: list[str],
    freshness_hours: float,
    now: datetime | None = None,
) -> list[JobPosting]:
    now = now or datetime.now(timezone.utc)
    seen: set[str] = set()
    result: list[JobPosting] = []
    for posting in postings:
        if posting.age_hours(now) > freshness_hours:
            continue
        if not matches_keywords(posting, keywords):
            continue
        if not matches_locations(posting, locations):
            continue
        if posting.dedup_key in seen:
            continue
        seen.add(posting.dedup_key)
        result.append(posting)

    result.sort(key=lambda p: p.posted_at, reverse=True)
    return result
