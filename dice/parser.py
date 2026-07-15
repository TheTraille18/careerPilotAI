from __future__ import annotations

import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

DICE_JOB_LINK_RE = re.compile(r"elinks\.dice\.com/a/sc/")
DICE_POSTED_RE = re.compile(r"posted:\s*(.+)$", re.I)
DICE_SKIP_TITLES = {
    "log in",
    "view all recommended jobs",
    "unsubscribe",
    "dice knowledge center",
}


def parse_posted_date(raw: str) -> datetime | None:
    raw = raw.strip()
    for fmt in ("%m-%d-%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def parse_dice_jobs(soup: BeautifulSoup) -> list[dict]:
    jobs: list[dict] = []
    seen_urls: set[str] = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        title = link.get_text(" ", strip=True)

        if not title or title.lower() in DICE_SKIP_TITLES:
            continue
        if not DICE_JOB_LINK_RE.search(href):
            continue
        if href in seen_urls:
            continue

        seen_urls.add(href)

        table = link.find_parent("table")
        if not table:
            continue

        lines = [line.strip() for line in table.get_text("\n", strip=True).splitlines() if line.strip()]
        if not lines:
            continue

        company = lines[1] if len(lines) > 1 else ""
        location = lines[2] if len(lines) > 2 else ""
        posted_date = None

        for line in lines[3:]:
            match = DICE_POSTED_RE.match(line)
            if match:
                posted_date = parse_posted_date(match.group(1))
                break

        jobs.append(
            {
                "title": title,
                "company": company,
                "location": location,
                "url": href,
                "posted_date": posted_date,
            }
        )

    return jobs
