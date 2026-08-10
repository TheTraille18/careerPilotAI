from __future__ import annotations

import re

from bs4 import BeautifulSoup

AIAPPLY_JOB_LINK_RE = re.compile(
    r"(aiapply\.co|go\.aiapply\.co|links\.aiapply\.co)",
    re.I,
)
AIAPPLY_SKIP_TITLES = {
    "apply now",
    "view job",
    "view all jobs",
    "view more",
    "see all",
    "unsubscribe",
    "manage preferences",
    "update preferences",
    "manage email settings",
    "privacy policy",
    "terms",
    "aiapply",
    "ai apply",
    "log in",
    "sign in",
    "get started",
    "learn more",
}


def parse_aiapply_jobs(soup: BeautifulSoup) -> list[dict]:
    """Parse AIApply job-alert emails into title/company/location/url dicts."""
    jobs: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        title = " ".join(link.get_text(" ", strip=True).split())

        if not title or title.lower() in AIAPPLY_SKIP_TITLES:
            continue
        if not AIAPPLY_JOB_LINK_RE.search(href):
            continue

        table = link.find_parent("table")
        if not table:
            continue

        lines = [line.strip() for line in table.get_text("\n", strip=True).splitlines() if line.strip()]
        if len(lines) < 2:
            continue

        job_title = title if title in lines else lines[0]
        try:
            title_index = lines.index(job_title)
        except ValueError:
            title_index = 0
            job_title = lines[0]

        company = ""
        location = ""
        if title_index + 1 < len(lines):
            company = lines[title_index + 1]
        if title_index + 2 < len(lines):
            location = lines[title_index + 2]

        if company.lower() in AIAPPLY_SKIP_TITLES or company.lower().startswith("$"):
            company = ""
            location = ""
        if location.lower() in AIAPPLY_SKIP_TITLES or location.lower().startswith("$"):
            location = ""

        key = (job_title.lower(), company.lower(), location.lower())
        if key in seen_keys:
            continue
        seen_keys.add(key)

        jobs.append(
            {
                "title": job_title,
                "company": company,
                "location": location,
                "url": href,
            }
        )

    return jobs
