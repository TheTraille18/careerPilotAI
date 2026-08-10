from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

REMOTE_ROCKETSHIP_LINK_RE = re.compile(r"click\.mailersend\.net|remoterocketship\.com", re.I)

SKIP_TITLES = {
    "edit your search requirements",
    "view all jobs",
    "view job",
    "unsubscribe",
    "manage preferences",
    "update preferences",
    "remote rocketship",
    "view more",
    "see all",
    "hi justin",
}


def _is_meta_line(line: str) -> bool:
    lowered = line.lower().strip()
    if not lowered:
        return True
    if lowered in SKIP_TITLES:
        return True
    if lowered.startswith(("💵", "🕒", "🚫", "$")):
        return True
    if "posted" in lowered and ("hour" in lowered or "day" in lowered or "ago" in lowered):
        return True
    if "linkedin" in lowered:
        return True
    return False


def parse_posted_date(raw: str) -> datetime | None:
    """Parse lines like '🕒 Posted 8 hours ago' into an approximate UTC timestamp."""
    text = raw.strip()
    match = re.search(r"posted\s+(\d+)\s+(minute|minutes|hour|hours|day|days)\s+ago", text, re.I)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).lower()
    now = datetime.now(timezone.utc)

    if unit.startswith("minute"):
        return now - timedelta(minutes=amount)
    if unit.startswith("hour"):
        return now - timedelta(hours=amount)
    if unit.startswith("day"):
        return now - timedelta(days=amount)
    return None


def _extract_default_location(soup: BeautifulSoup) -> str:
    lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if line.lower().rstrip(":") == "locations" and index + 1 < len(lines):
            location = lines[index + 1]
            # Strip leading emoji flags / symbols.
            return re.sub(r"^[^\w$]+", "", location).strip() or "Remote"
    return "Remote"


def parse_remoterocketship_jobs(soup: BeautifulSoup) -> list[dict]:
    jobs: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()
    default_location = _extract_default_location(soup)

    for link in soup.find_all("a", href=True):
        href = link["href"]
        title = " ".join(link.get_text(" ", strip=True).split())

        if not title or title.lower() in SKIP_TITLES:
            continue
        if not REMOTE_ROCKETSHIP_LINK_RE.search(href):
            continue

        card_lines: list[str] | None = None
        node = link
        for _ in range(8):
            node = node.find_parent("table")
            if not node:
                break
            lines = [line.strip() for line in node.get_text("\n", strip=True).splitlines() if line.strip()]
            if not lines or lines[0] != title:
                continue
            if 3 <= len(lines) <= 10:
                card_lines = lines
                break

        if not card_lines:
            continue

        company = ""
        location = default_location
        posted_date = None

        for line in card_lines[1:]:
            if _is_meta_line(line):
                if posted_date is None:
                    posted_date = parse_posted_date(line)
                continue
            if not company:
                company = line
                continue

        # Prefer the "View job" link URL when present in the same card.
        view_job_url = href
        card_table = link.find_parent("table")
        if card_table:
            for card_link in card_table.find_all("a", href=True):
                label = " ".join(card_link.get_text(" ", strip=True).split()).lower()
                if label == "view job" and card_link.get("href"):
                    view_job_url = card_link["href"]
                    break

        key = (title.lower(), company.lower(), location.lower())
        if key in seen_keys:
            continue
        seen_keys.add(key)

        jobs.append(
            {
                "title": title,
                "company": company,
                "location": location,
                "url": view_job_url,
                "posted_date": posted_date,
            }
        )

    return jobs
