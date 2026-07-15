from __future__ import annotations

from careerbuilder.parser import parse_careerbuilder_jobs
from email_utils import fetch_jobs
from models import JobListing


def fetch_careerbuilder_jobs(
    service,
    *,
    max_results: int = 10,
    days: int | None = None,
) -> list[JobListing]:
    query = "label:Jobs-Careerbuilder"
    if days is not None:
        query = f"{query} newer_than:{days}d"

    return fetch_jobs(
        service,
        query=query,
        parser=parse_careerbuilder_jobs,
        source="careerbuilder",
        max_results=max_results,
    )
