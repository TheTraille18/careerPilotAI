from __future__ import annotations

import re

from bs4 import BeautifulSoup

INDEED_JOB_LINK_RE = re.compile(
    r"(indeed\.com/(?:pagead/clk|viewjob|rc/clk)|cts\.indeed\.com)",
    re.I,
)
INDEED_SKIP_TITLES = {
    "find jobs",
    "sign in",
    "view job",
    "view more jobs",
    "learn more",
    "easily apply",
    "this is a bad match",
    "pause these emails",
    "manage email settings",
    "help center",
    "unsubscribe",
    "privacy policy",
    "terms",
    "indeed",
    "your privacy choices",
    "edit profile",
    "yes",
    "no",
}


def parse_indeed_jobs(soup: BeautifulSoup) -> list[dict]:
    jobs: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        title = link.get_text(" ", strip=True)

        if not title or title.lower() in INDEED_SKIP_TITLES:
            continue
        if not INDEED_JOB_LINK_RE.search(href):
            continue

        table = link.find_parent("table")
        if not table:
            continue

        lines = [line.strip() for line in table.get_text("\n", strip=True).splitlines() if line.strip()]
        if len(lines) < 2:
            continue

        # Prefer the link text as title; fall back to first table line.
        job_title = title if title in lines else lines[0]
        company = ""
        location = ""

        try:
            title_index = lines.index(job_title)
        except ValueError:
            title_index = 0
            job_title = lines[0]

        if title_index + 1 < len(lines):
            company = lines[title_index + 1]
        if title_index + 2 < len(lines):
            location = lines[title_index + 2]

        # Skip salary / CTA lines mistaken as company/location.
        if company.lower() in INDEED_SKIP_TITLES or company.lower().startswith("$"):
            company = ""
            location = ""
        if location.lower() in INDEED_SKIP_TITLES or location.lower().startswith("$"):
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
