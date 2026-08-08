from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from job_id import make_job_id
from models import JobListing


def decode_body_data(data: str) -> str:
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")


def find_html_part(payload: dict) -> str | None:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if body_data and mime_type == "text/html":
        return decode_body_data(body_data)

    for part in payload.get("parts", []):
        html = find_html_part(part)
        if html:
            return html

    return None


def find_text_part(payload: dict) -> str | None:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if body_data and mime_type == "text/plain":
        return decode_body_data(body_data)

    for part in payload.get("parts", []):
        text = find_text_part(part)
        if text:
            return text

    return None


def message_body_text(msg: dict, *, max_chars: int = 4000) -> str:
    """Prefer plain text; fall back to HTML stripped to text. Truncate for LLM prompts."""
    payload = msg.get("payload", {}) or {}
    text = find_text_part(payload)
    if not text:
        html = find_html_part(payload)
        if html:
            text = BeautifulSoup(html, "lxml").get_text("\n", strip=True)
    text = (text or "").strip()
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


def header_value(headers: list[dict], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def get_email_date(msg: dict) -> datetime | None:
    headers = msg.get("payload", {}).get("headers") or []
    raw_date = header_value(headers, "Date")
    if raw_date:
        try:
            dt = parsedate_to_datetime(raw_date)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except (TypeError, ValueError, OverflowError):
            pass

    internal_date = msg.get("internalDate")
    if internal_date:
        return datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)

    return None


def fetch_jobs(
    service,
    *,
    query: str,
    parser,
    source: str,
    max_results: int = 10,
) -> list[JobListing]:
    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )

    listings: list[JobListing] = []
    message_refs = results.get("messages") or []

    for message_ref in message_refs:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message_ref["id"], format="full")
            .execute()
        )

        html = find_html_part(msg.get("payload", {}))
        if not html:
            continue

        email_date = get_email_date(msg)
        soup = BeautifulSoup(html, "lxml")

        for job in parser(soup):
            title = job["title"]
            company = job["company"]
            location = job["location"]
            listings.append(
                JobListing(
                    title=title,
                    company=company,
                    location=location,
                    date=job.get("posted_date") or email_date,
                    url=job["url"],
                    email_id=msg["id"],
                    source=source,
                    job_id=make_job_id(title, company, location),
                    status="Active",
                    job_description="Not available",
                    analysis_status="Pending",
                    applied="No",
                )
            )

    return listings


def format_date(dt: datetime | None) -> str:
    if not dt:
        return "unknown"
    return dt.astimezone().strftime("%Y-%m-%d %H:%M %Z")
