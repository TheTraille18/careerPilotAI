"""Skip / remove jobs whose titles are senior-level roles."""

from __future__ import annotations

import re

# Whole-word matches (case-insensitive): "Staff Engineer" yes, "Leadership" no.
EXCLUDED_TITLE_WORDS = ("Lead", "Staff", "Principal", "Director", "Manager")

_EXCLUDED_TITLE_RE = re.compile(
    r"\b(" + "|".join(re.escape(word) for word in EXCLUDED_TITLE_WORDS) + r")\b",
    re.IGNORECASE,
)


def is_excluded_title(title: str | None) -> bool:
    """True if the title contains Lead, Staff, Principal, or Director as a word."""
    return bool(_EXCLUDED_TITLE_RE.search(title or ""))
