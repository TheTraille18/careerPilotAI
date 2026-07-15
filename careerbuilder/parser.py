from __future__ import annotations

import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

CAREERBUILDER_JOB_LINK_RE = re.compile(
    r"careerbuilder\.et\.e\.sparkpost\.com|careerbuilder\.com",
    re.I,
)
CAREERBUILDER_SKIP_TITLES = {
    "apply now",
    "update my settings",
    "view all latest matches",
    "manage my preferences",
    "unsubscribe",
    "update my",
}


def parse_posted_date(raw: str) -> datetime | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        # CareerBuilder emails use ISO timestamps like 2026-07-08T01:00:00.000Z
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw).astimezone(timezone.utc)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def parse_careerbuilder_jobs(soup: BeautifulSoup) -> list[dict]:
    jobs: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        title = " ".join(link.get_text(" ", strip=True).split())

        if not title or title.lower() in CAREERBUILDER_SKIP_TITLES:
            continue
        if not CAREERBUILDER_JOB_LINK_RE.search(href):
            continue

        table = link.find_parent("table")
        if not table:
            continue

        lines = [line.strip() for line in table.get_text("\n", strip=True).splitlines() if line.strip()]
        if len(lines) < 2:
            continue

        company = lines[1] if len(lines) > 1 else ""
        location = lines[2] if len(lines) > 2 else ""
        posted_date = None

        for index, line in enumerate(lines):
            if line.lower().rstrip(":") == "posted" and index + 1 < len(lines):
                posted_date = parse_posted_date(lines[index + 1])
                break
            if line.lower().startswith("posted:"):
                posted_date = parse_posted_date(line.split(":", 1)[1])
                break

        if company.lower() in CAREERBUILDER_SKIP_TITLES:
            company = ""
        if location.lower() in CAREERBUILDER_SKIP_TITLES or location.lower() == "posted:":
            location = ""

        key = (title.lower(), company.lower(), location.lower())
        if key in seen_keys:
            continue
        seen_keys.add(key)

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
