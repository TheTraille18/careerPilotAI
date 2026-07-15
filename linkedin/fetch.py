from __future__ import annotations

from email_utils import fetch_jobs
from linkedin.parser import parse_linkedin_jobs
from models import JobListing


def fetch_linkedin_jobs(
    service,
    *,
    max_results: int = 10,
    days: int | None = None,
) -> list[JobListing]:
    query = "label:jobs-linkedin"
    if days is not None:
        query = f"{query} newer_than:{days}d"

    return fetch_jobs(
        service,
        query=query,
        parser=parse_linkedin_jobs,
        source="linkedin",
        max_results=max_results,
    )
