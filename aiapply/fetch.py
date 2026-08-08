from __future__ import annotations

from aiapply.parser import parse_aiapply_jobs
from email_utils import fetch_jobs
from models import JobListing


def fetch_aiapply_jobs(
    service,
    *,
    max_results: int = 10,
    days: int | None = None,
) -> list[JobListing]:
    # Nested Gmail label Jobs/AiApply → search as Jobs-AiApply (same as CareerBuilder).
    query = "label:Jobs-AiApply"
    if days is not None:
        query = f"{query} newer_than:{days}d"

    return fetch_jobs(
        service,
        query=query,
        parser=parse_aiapply_jobs,
        source="aiapply",
        max_results=max_results,
    )
