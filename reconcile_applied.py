from __future__ import annotations

from dynamodb_store import list_jobs, mark_listing_applied
from job_id import application_match_key

AIAPPLY_SOURCE = "aiapply"


def reconcile_applied(*, table_name: str | None = None) -> dict:
    """Mark LinkedIn/Dice/etc listings Applied when they match an AIApply application.

    Matching is on normalized title + company (location ignored).
    AIApply rows are the applied ledger and are left unchanged.
    """
    jobs = list_jobs(table_name=table_name)

    applied_by_key: dict[tuple[str, str], dict] = {}
    for job in jobs:
        if job.get("source") != AIAPPLY_SOURCE:
            continue
        key = application_match_key(job.get("title") or "", job.get("company") or "")
        if not key[0] or not key[1]:
            continue
        # Prefer the earliest applied_date if duplicates exist
        existing = applied_by_key.get(key)
        if not existing:
            applied_by_key[key] = job
            continue
        existing_date = existing.get("appliedDate") or existing.get("date") or ""
        new_date = job.get("appliedDate") or job.get("date") or ""
        if new_date and (not existing_date or new_date < existing_date):
            applied_by_key[key] = job

    marked: list[dict] = []
    already_applied = 0
    checked = 0

    for job in jobs:
        source = job.get("source") or ""
        if source == AIAPPLY_SOURCE:
            continue

        checked += 1
        key = application_match_key(job.get("title") or "", job.get("company") or "")
        match = applied_by_key.get(key)
        if not match:
            continue

        if str(job.get("applied") or "").lower() == "yes" or job.get("status") == "Applied":
            already_applied += 1
            continue

        updated = mark_listing_applied(
            job["jobId"],
            source,
            applied_date=str(match.get("appliedDate") or ""),
            table_name=table_name,
        )
        marked.append(
            {
                "jobId": updated.get("jobId"),
                "source": updated.get("source"),
                "title": updated.get("title"),
                "company": updated.get("company"),
                "matchedAiApplyEmailId": match.get("emailId") or "",
            }
        )

    return {
        "aiapplyApplications": len(applied_by_key),
        "listingsChecked": checked,
        "markedApplied": len(marked),
        "alreadyApplied": already_applied,
        "matches": marked,
    }
