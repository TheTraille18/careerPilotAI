from __future__ import annotations

import re

from bs4 import BeautifulSoup

JOB_ID_RE = re.compile(r"/jobs/view/(\d+)")
SKIP_DETAIL_LINES = re.compile(
    r"^(actively recruiting|fast growing|\d+ connection|\$[\d,]+k?/ year)$",
    re.I,
)
COMPANY_LOCATION_SEPARATORS = ("\u00b7", "|", " - ")


def split_company_location(line: str) -> tuple[str, str]:
    line = line.strip()
    for sep in COMPANY_LOCATION_SEPARATORS:
        if sep in line:
            company, location = line.split(sep, 1)
            return company.strip(), location.strip()
    return line.strip(), ""


def clean_detail_lines(lines: list[str]) -> list[str]:
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if SKIP_DETAIL_LINES.match(stripped):
            continue
        cleaned.append(stripped)
    return cleaned


def parse_linkedin_jobs(soup: BeautifulSoup) -> list[dict]:
    jobs_by_id: dict[str, dict] = {}

    for link in soup.find_all("a", href=True):
        href = link["href"]
        match = JOB_ID_RE.search(href)
        if not match:
            continue

        job_id = match.group(1)
        row = link.find_parent("tr")
        block_text = row.get_text("\n", strip=True) if row else link.get_text("\n", strip=True)
        lines = clean_detail_lines(block_text.splitlines())

        if not lines:
            continue

        if job_id not in jobs_by_id or len(lines) > len(jobs_by_id[job_id]["lines"]):
            jobs_by_id[job_id] = {
                "lines": lines,
                "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
            }

    jobs: list[dict] = []
    for job_id, data in jobs_by_id.items():
        lines = data["lines"]
        title = lines[0]
        company, location = "", ""

        if len(lines) >= 2:
            company, location = split_company_location(lines[1])

        jobs.append(
            {
                "title": title,
                "company": company,
                "location": location,
                "url": data["url"],
            }
        )

    return jobs
