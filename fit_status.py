from __future__ import annotations

FIT_STATUSES = (
    "Unset",
    "Apply",
    "Maybe",
    "Skip",
)

DEFAULT_FIT_STATUS = "Unset"


def normalize_fit_status(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return DEFAULT_FIT_STATUS
    for status in FIT_STATUSES:
        if text.lower() == status.lower():
            return status
    return DEFAULT_FIT_STATUS
