from __future__ import annotations

from dice.parser import parse_dice_jobs
from email_utils import fetch_jobs
from models import JobListing


def fetch_dice_jobs(
    service,
    *,
    max_results: int = 10,
    days: int | None = None,
) -> list[JobListing]:
    query = "label:jobs-dice"
    if days is not None:
        query = f"{query} newer_than:{days}d"

    return fetch_jobs(
        service,
        query=query,
        parser=parse_dice_jobs,
        source="dice",
        max_results=max_results,
    )
