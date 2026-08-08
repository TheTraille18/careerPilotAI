from __future__ import annotations

JOB_STATUSES = (
    "Active",
    "Applied",
    "Interview",
    "Offer",
    "Rejected",
    "Closed",
    "Not Enough Experience",
)

DEFAULT_JOB_STATUS = "Active"


def normalize_job_status(value: str | None) -> str:
    text = (value or "").strip()
    if text in JOB_STATUSES:
        return text
    if text in {"", "active"}:
        return DEFAULT_JOB_STATUS
    # Keep unknown legacy values readable in the UI by falling back to Active
    # only when empty; otherwise preserve known casing if it matches ignoring case.
    for status in JOB_STATUSES:
        if text.lower() == status.lower():
            return status
    return DEFAULT_JOB_STATUS
