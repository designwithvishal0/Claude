from __future__ import annotations

import os

from ..models import JobPosting
from .base import JobSource


class ZipRecruiterSource(JobSource):
    """ZipRecruiter via their official Jobs API.

    Requires a ZipRecruiter partner/API key; the public endpoint this
    project probed returned 404 without one, so the exact current request
    shape needs to come from your own partner docs rather than being
    guessed here.

    To enable: get API access from ZipRecruiter, set ZIPRECRUITER_API_KEY,
    and fill in `fetch()` against the endpoint your account is given.
    """

    name = "ziprecruiter"

    def fetch(self) -> list[JobPosting]:
        if not os.environ.get("ZIPRECRUITER_API_KEY"):
            return []
        raise NotImplementedError(
            "ZIPRECRUITER_API_KEY is set, but src/sources/ziprecruiter.py has "
            "no request implementation yet — fill it in against your partner "
            "account's actual endpoint and response shape."
        )
