from __future__ import annotations

from email_utils import fetch_jobs
from indeed.parser import parse_indeed_jobs
from models import JobListing


def fetch_indeed_jobs(
    service,
    *,
    max_results: int = 10,
    days: int | None = None,
) -> list[JobListing]:
    query = "label:jobs-indeed"
    if days is not None:
        query = f"{query} newer_than:{days}d"

    return fetch_jobs(
        service,
        query=query,
        parser=parse_indeed_jobs,
        source="indeed",
        max_results=max_results,
    )
