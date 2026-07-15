from __future__ import annotations

import hashlib
import re

US_STATE_NAMES: dict[str, str] = {
    "alabama": "al",
    "alaska": "ak",
    "arizona": "az",
    "arkansas": "ar",
    "california": "ca",
    "colorado": "co",
    "connecticut": "ct",
    "delaware": "de",
    "district of columbia": "dc",
    "florida": "fl",
    "georgia": "ga",
    "hawaii": "hi",
    "idaho": "id",
    "illinois": "il",
    "indiana": "in",
    "iowa": "ia",
    "kansas": "ks",
    "kentucky": "ky",
    "louisiana": "la",
    "maine": "me",
    "maryland": "md",
    "massachusetts": "ma",
    "michigan": "mi",
    "minnesota": "mn",
    "mississippi": "ms",
    "missouri": "mo",
    "montana": "mt",
    "nebraska": "ne",
    "nevada": "nv",
    "new hampshire": "nh",
    "new jersey": "nj",
    "new mexico": "nm",
    "new york": "ny",
    "north carolina": "nc",
    "north dakota": "nd",
    "ohio": "oh",
    "oklahoma": "ok",
    "oregon": "or",
    "pennsylvania": "pa",
    "rhode island": "ri",
    "south carolina": "sc",
    "south dakota": "sd",
    "tennessee": "tn",
    "texas": "tx",
    "utah": "ut",
    "vermont": "vt",
    "virginia": "va",
    "washington": "wa",
    "west virginia": "wv",
    "wisconsin": "wi",
    "wyoming": "wy",
}

US_STATE_ABBREVS = set(US_STATE_NAMES.values())

# Longer names first so "new york" matches before "york"
_STATE_NAME_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(US_STATE_NAMES.keys(), key=len, reverse=True)) + r")\b",
    re.I,
)
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.strip().lower())


def normalize_location(value: str) -> str:
    location = normalize_text(value)

    def replace_state_name(match: re.Match[str]) -> str:
        return US_STATE_NAMES[match.group(1).lower()]

    location = _STATE_NAME_PATTERN.sub(replace_state_name, location)

    # Normalize standalone 2-letter state tokens (already lowercase)
    parts = re.split(r"([^a-z0-9]+)", location)
    normalized_parts: list[str] = []
    for part in parts:
        if part in US_STATE_ABBREVS:
            normalized_parts.append(part)
        else:
            normalized_parts.append(part)

    return "".join(normalized_parts)


def make_job_id(title: str, company: str, location: str) -> str:
    """Stable hash of normalized title + company + location."""
    key = "|".join(
        [
            normalize_text(title),
            normalize_text(company),
            normalize_location(location),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
