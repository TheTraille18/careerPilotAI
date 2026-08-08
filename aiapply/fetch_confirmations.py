from __future__ import annotations

from dynamodb_store import list_email_ids
from email_utils import (
    get_email_date,
    header_value,
    message_body_text,
)
from job_id import make_job_id
from models import JobListing

from aiapply.extract import extract_application, is_usable_extraction


def fetch_aiapply_confirmations(
    service,
    *,
    max_results: int = 50,
    days: int | None = None,
    min_confidence: float = 0.5,
    skip_email_ids: set[str] | None = None,
    skip_existing: bool = True,
) -> list[JobListing]:
    """Fetch AIApply confirmation emails and extract title/company via Bedrock.

    By default skips Gmail message ids already stored under source=aiapply so
    Bedrock runs at most once per confirmation email.
    """
    query = "label:Jobs-AiApply"
    if days is not None:
        query = f"{query} newer_than:{days}d"

    known_ids = set(skip_email_ids or ())
    if skip_existing:
        known_ids |= list_email_ids(source="aiapply")

    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )

    listings: list[JobListing] = []
    message_refs = results.get("messages") or []
    skipped_existing = 0

    for message_ref in message_refs:
        email_id = message_ref["id"]
        if email_id in known_ids:
            skipped_existing += 1
            continue

        msg = (
            service.users()
            .messages()
            .get(userId="me", id=email_id, format="full")
            .execute()
        )

        headers = msg.get("payload", {}).get("headers") or []
        subject = header_value(headers, "Subject")
        body = message_body_text(msg)
        if not subject and not body:
            continue

        try:
            extracted = extract_application(subject, body)
        except Exception as exc:
            print(f"  skip {email_id}: extraction failed: {exc}")
            continue

        if not is_usable_extraction(extracted, min_confidence=min_confidence):
            print(
                f"  skip {email_id}: low confidence or missing fields "
                f"(title={extracted.get('title')!r}, company={extracted.get('company')!r}, "
                f"confidence={extracted.get('confidence')})"
            )
            continue

        title = extracted["title"]
        company = extracted["company"]
        location = ""
        email_date = get_email_date(msg)
        applied_date = email_date.date().isoformat() if email_date else ""

        listings.append(
            JobListing(
                title=title,
                company=company,
                location=location,
                date=email_date,
                url="",
                email_id=email_id,
                source="aiapply",
                job_id=make_job_id(title, company, location),
                status="Applied",
                job_description="Not available",
                analysis_status="Pending",
                applied="Yes",
                applied_date=applied_date,
            )
        )

    if skipped_existing:
        print(f"  skipped {skipped_existing} already-extracted AIApply email(s)")

    return listings
