from __future__ import annotations

ANALYSIS_STATUSES = (
    "Pending",
    "Tailored Resume",
    "Cover Letter",
)

DEFAULT_ANALYSIS_STATUS = "Pending"


def normalize_analysis_status(value: str | None) -> str:
    text = (value or "").strip()
    if text in ANALYSIS_STATUSES:
        return text
    # Legacy default from earlier versions
    if text in {"", "Not Started", "NotStarted"}:
        return DEFAULT_ANALYSIS_STATUS
    return DEFAULT_ANALYSIS_STATUS
