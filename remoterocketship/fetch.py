from __future__ import annotations

from email_utils import fetch_jobs
from remoterocketship.parser import parse_remoterocketship_jobs
from models import JobListing


def fetch_remoterocketship_jobs(
    service,
    *,
    max_results: int = 10,
    days: int | None = None,
) -> list[JobListing]:
    query = "label:jobs-remoterocketship"
    if days is not None:
        query = f"{query} newer_than:{days}d"

    return fetch_jobs(
        service,
        query=query,
        parser=parse_remoterocketship_jobs,
        source="remoterocketship",
        max_results=max_results,
    )
