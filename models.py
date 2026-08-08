from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from analysis_status import DEFAULT_ANALYSIS_STATUS


@dataclass
class JobListing:
    title: str
    company: str
    location: str
    date: datetime | None
    url: str
    email_id: str
    source: str
    job_id: str
    status: str = "Active"
    job_description: str = "Not available"
    analysis_status: str = DEFAULT_ANALYSIS_STATUS
    applied: str = "No"
    applied_date: str = ""
