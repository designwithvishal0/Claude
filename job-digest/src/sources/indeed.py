from __future__ import annotations

import os

from ..models import JobPosting
from .base import JobSource


class IndeedSource(JobSource):
    """Indeed via an official partner API.

    Indeed's old consumer Publisher API is retired; current job-search
    access goes through Indeed's partner program, which issues per-partner
    credentials and endpoints. This project has none, so implementing a
    fixed endpoint here would just be guessing at something likely to
    silently break.

    To enable: get partner API access from Indeed, set the credentials
    below as env vars, and fill in `fetch()` against the endpoint and
    response shape your agreement actually gives you.
    """

    name = "indeed"

    def fetch(self) -> list[JobPosting]:
        if not os.environ.get("INDEED_PARTNER_API_KEY"):
            return []
        raise NotImplementedError(
            "INDEED_PARTNER_API_KEY is set, but src/sources/indeed.py has no "
            "request implementation yet — fill it in against your partner "
            "agreement's actual endpoint and response shape."
        )
