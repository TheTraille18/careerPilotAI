from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from models import JobListing
from analysis_status import DEFAULT_ANALYSIS_STATUS, normalize_analysis_status
from config import get_local_today_iso
from job_id import make_job_id
from job_status import DEFAULT_JOB_STATUS, normalize_job_status
from job_title_filters import is_excluded_title

DEFAULT_TABLE_NAME = "careerpilotai_db"
DEFAULT_REGION = "us-east-1"

# Must match the live table AttributeDefinitions / KeySchema.
PARTITION_KEY = "job_id"
SORT_KEY = "source"


def get_table_name() -> str:
    return os.getenv("CAREERPILOT_JOBS_TABLE", DEFAULT_TABLE_NAME)


def get_dynamodb_resource():
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or DEFAULT_REGION
    return boto3.resource("dynamodb", region_name=region)


def ensure_jobs_table(table_name: str | None = None) -> str:
    """Create the jobs table if it does not already exist.

    Primary key: job_id (HASH)
    Sort key:    source (RANGE)
    """
    table_name = table_name or get_table_name()
    dynamodb = get_dynamodb_resource()
    client = dynamodb.meta.client

    try:
        client.describe_table(TableName=table_name)
        return table_name
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": PARTITION_KEY, "KeyType": "HASH"},
            {"AttributeName": SORT_KEY, "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": PARTITION_KEY, "AttributeType": "S"},
            {"AttributeName": SORT_KEY, "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()
    return table_name


def job_to_item(job: JobListing) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    item = {
        PARTITION_KEY: job.job_id,
        SORT_KEY: job.source,
        "title": job.title,
        "company": job.company or "",
        "location": job.location or "",
        "url": job.url,
        "email_id": job.email_id,
        "Status": job.status,
        "JobDescription": job.job_description,
        "AnalysisStatus": normalize_analysis_status(job.analysis_status),
        "Applied": job.applied,
        "updated_at": now,
    }
    if job.applied_date:
        item["AppliedDate"] = job.applied_date
    if job.date is not None:
        item["date"] = job.date.astimezone(timezone.utc).isoformat()
    return item


def item_to_job_dict(item: dict) -> dict:
    status = item.get("Status")
    if status is None:
        status = item.get("status")
    if not status:
        status = "Active"
    status = normalize_job_status(str(status))

    job_description = item.get("JobDescription")
    if job_description is None:
        job_description = item.get("job_description")
    if not job_description:
        job_description = "Not available"

    analysis_status = normalize_analysis_status(
        item.get("AnalysisStatus")
        if item.get("AnalysisStatus") is not None
        else item.get("analysis_status")
    )

    applied = item.get("Applied")
    if applied is None:
        applied = item.get("applied")
    if not applied:
        applied = "No"

    applied_date = item.get("AppliedDate")
    if applied_date is None:
        applied_date = item.get("applied_date") or item.get("appliedDate")
    if not applied_date:
        applied_date = ""

    eval_result = None
    raw_eval = item.get("EvalResult")
    if raw_eval is None:
        raw_eval = item.get("evalResult") or item.get("eval_result")
    if isinstance(raw_eval, dict):
        eval_result = raw_eval
    elif isinstance(raw_eval, str) and raw_eval.strip():
        try:
            parsed = json.loads(raw_eval)
            if isinstance(parsed, dict):
                eval_result = parsed
        except json.JSONDecodeError:
            eval_result = None

    return {
        "jobId": item.get(PARTITION_KEY, ""),
        "title": item.get("title", ""),
        "company": item.get("company", ""),
        "location": item.get("location", ""),
        "date": item.get("date", ""),
        "url": item.get("url", ""),
        "source": item.get(SORT_KEY, ""),
        "status": str(status),
        "jobDescription": str(job_description),
        "analysisStatus": analysis_status,
        "applied": str(applied),
        "appliedDate": str(applied_date),
        "emailId": item.get("email_id", ""),
        "updatedAt": item.get("updated_at", ""),
        "evalResult": eval_result,
    }


def list_jobs(*, table_name: str | None = None) -> list[dict]:
    """Scan all jobs from DynamoDB, newest first."""
    table_name = table_name or get_table_name()
    table = get_dynamodb_resource().Table(table_name)

    items: list[dict] = []
    response = table.scan()
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    jobs = [item_to_job_dict(item) for item in items]
    jobs.sort(key=lambda job: job.get("date") or job.get("updatedAt") or "", reverse=True)
    return jobs


def list_email_ids(
    *,
    source: str | None = None,
    table_name: str | None = None,
) -> set[str]:
    """Return email_id values already stored (optionally filtered by source)."""
    jobs = list_jobs(table_name=table_name)
    ids: set[str] = set()
    for job in jobs:
        if source and job.get("source") != source:
            continue
        email_id = (job.get("emailId") or "").strip()
        if email_id:
            ids.add(email_id)
    return ids


def mark_listing_applied(
    job_id: str,
    source: str,
    *,
    applied_date: str = "",
    table_name: str | None = None,
) -> dict:
    """Mark a listing Applied=Yes with Status=Applied.

    AppliedDate uses applied_date when provided, otherwise today's local date,
    and never overwrites an existing AppliedDate.
    """
    table_name = table_name or get_table_name()
    table = get_dynamodb_resource().Table(table_name)
    now = datetime.now(timezone.utc).isoformat()
    date_value = (applied_date or "").strip() or get_local_today_iso()

    try:
        response = table.update_item(
            Key={PARTITION_KEY: job_id, SORT_KEY: source},
            UpdateExpression=(
                "SET #status = :status, Applied = :applied, "
                "AppliedDate = if_not_exists(AppliedDate, :applied_date), "
                "updated_at = :updated"
            ),
            ConditionExpression="attribute_exists(#jid) AND attribute_exists(#src)",
            ExpressionAttributeNames={
                "#jid": PARTITION_KEY,
                "#src": SORT_KEY,
                "#status": "Status",
            },
            ExpressionAttributeValues={
                ":status": "Applied",
                ":applied": "Yes",
                ":applied_date": date_value,
                ":updated": now,
            },
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise KeyError(f"Job not found: {job_id}/{source}") from exc
        raise

    return item_to_job_dict(response["Attributes"])


def get_job(job_id: str, source: str, *, table_name: str | None = None) -> dict:
    """Fetch one job by (job_id, source). Raises KeyError if missing."""
    table_name = table_name or get_table_name()
    table = get_dynamodb_resource().Table(table_name)
    response = table.get_item(Key={PARTITION_KEY: job_id, SORT_KEY: source})
    item = response.get("Item")
    if not item:
        raise KeyError(f"Job not found: {job_id}/{source}")
    return item_to_job_dict(item)


def update_job_description(
    job_id: str,
    source: str,
    job_description: str,
    *,
    table_name: str | None = None,
) -> dict:
    """Update JobDescription for one job. Empty text becomes 'Not available'."""
    table_name = table_name or get_table_name()
    table = get_dynamodb_resource().Table(table_name)
    text = (job_description or "").strip() or "Not available"
    now = datetime.now(timezone.utc).isoformat()

    try:
        response = table.update_item(
            Key={PARTITION_KEY: job_id, SORT_KEY: source},
            UpdateExpression="SET JobDescription = :desc, updated_at = :updated",
            ConditionExpression="attribute_exists(#jid) AND attribute_exists(#src)",
            ExpressionAttributeNames={
                "#jid": PARTITION_KEY,
                "#src": SORT_KEY,
            },
            ExpressionAttributeValues={
                ":desc": text,
                ":updated": now,
            },
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise KeyError(f"Job not found: {job_id}/{source}") from exc
        raise

    return item_to_job_dict(response["Attributes"])


def update_analysis_status(
    job_id: str,
    source: str,
    analysis_status: str,
    *,
    table_name: str | None = None,
) -> dict:
    """Update AnalysisStatus for one job. Only allowed enum values are stored."""
    table_name = table_name or get_table_name()
    table = get_dynamodb_resource().Table(table_name)
    text = normalize_analysis_status(analysis_status)
    now = datetime.now(timezone.utc).isoformat()

    try:
        response = table.update_item(
            Key={PARTITION_KEY: job_id, SORT_KEY: source},
            UpdateExpression="SET AnalysisStatus = :status, updated_at = :updated",
            ConditionExpression="attribute_exists(#jid) AND attribute_exists(#src)",
            ExpressionAttributeNames={
                "#jid": PARTITION_KEY,
                "#src": SORT_KEY,
            },
            ExpressionAttributeValues={
                ":status": text,
                ":updated": now,
            },
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise KeyError(f"Job not found: {job_id}/{source}") from exc
        raise

    return item_to_job_dict(response["Attributes"])


def update_eval_result(
    job_id: str,
    source: str,
    eval_result: dict,
    *,
    table_name: str | None = None,
) -> dict:
    """Persist AI eval JSON for one job."""
    table_name = table_name or get_table_name()
    table = get_dynamodb_resource().Table(table_name)
    now = datetime.now(timezone.utc).isoformat()
    payload = dict(eval_result)
    payload["evaluatedAt"] = now

    try:
        response = table.update_item(
            Key={PARTITION_KEY: job_id, SORT_KEY: source},
            UpdateExpression="SET EvalResult = :eval, updated_at = :updated",
            ConditionExpression="attribute_exists(#jid) AND attribute_exists(#src)",
            ExpressionAttributeNames={
                "#jid": PARTITION_KEY,
                "#src": SORT_KEY,
            },
            ExpressionAttributeValues={
                ":eval": json.dumps(payload),
                ":updated": now,
            },
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise KeyError(f"Job not found: {job_id}/{source}") from exc
        raise

    return item_to_job_dict(response["Attributes"])


def update_applied(
    job_id: str,
    source: str,
    applied: str,
    *,
    table_name: str | None = None,
) -> dict:
    """Update Applied to Yes/No. When Yes, set AppliedDate if missing."""
    table_name = table_name or get_table_name()
    table = get_dynamodb_resource().Table(table_name)
    text = (applied or "").strip()
    if text.lower() in {"yes", "y", "true", "1"}:
        text = "Yes"
    else:
        text = "No"
    now = datetime.now(timezone.utc).isoformat()

    update_parts = ["Applied = :applied", "updated_at = :updated"]
    values: dict = {
        ":applied": text,
        ":updated": now,
    }

    if text == "Yes":
        applied_date = get_local_today_iso()
        update_parts.append("AppliedDate = if_not_exists(AppliedDate, :applied_date)")
        values[":applied_date"] = applied_date

    try:
        response = table.update_item(
            Key={PARTITION_KEY: job_id, SORT_KEY: source},
            UpdateExpression="SET " + ", ".join(update_parts),
            ConditionExpression="attribute_exists(#jid) AND attribute_exists(#src)",
            ExpressionAttributeNames={
                "#jid": PARTITION_KEY,
                "#src": SORT_KEY,
            },
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise KeyError(f"Job not found: {job_id}/{source}") from exc
        raise

    return item_to_job_dict(response["Attributes"])


def update_job_status(
    job_id: str,
    source: str,
    status: str,
    *,
    table_name: str | None = None,
) -> dict:
    """Update Status for one job. Only allowed enum values are stored.

    When status becomes Applied, also set Applied=Yes and AppliedDate (today)
    if AppliedDate is not already set.
    """
    table_name = table_name or get_table_name()
    table = get_dynamodb_resource().Table(table_name)
    text = normalize_job_status(status)
    now = datetime.now(timezone.utc).isoformat()

    update_parts = ["#status = :status", "updated_at = :updated"]
    names = {
        "#jid": PARTITION_KEY,
        "#src": SORT_KEY,
        "#status": "Status",
    }
    values: dict = {
        ":status": text,
        ":updated": now,
    }

    if text == "Applied":
        applied_date = get_local_today_iso()
        update_parts.extend(
            [
                "Applied = :applied",
                "AppliedDate = if_not_exists(AppliedDate, :applied_date)",
            ]
        )
        values[":applied"] = "Yes"
        values[":applied_date"] = applied_date

    try:
        response = table.update_item(
            Key={PARTITION_KEY: job_id, SORT_KEY: source},
            UpdateExpression="SET " + ", ".join(update_parts),
            ConditionExpression="attribute_exists(#jid) AND attribute_exists(#src)",
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise KeyError(f"Job not found: {job_id}/{source}") from exc
        raise

    return item_to_job_dict(response["Attributes"])


def _existing_item(table, job_id: str, source: str) -> dict | None:
    response = table.get_item(Key={PARTITION_KEY: job_id, SORT_KEY: source})
    return response.get("Item")


def _existing_job_description(table, job_id: str, source: str) -> str | None:
    item = _existing_item(table, job_id, source)
    if not item:
        return None
    value = item.get("JobDescription")
    if value is None:
        value = item.get("job_description")
    if not value:
        return None
    return str(value)


def put_jobs(jobs: list[JobListing], *, table_name: str | None = None) -> int:
    """Upsert jobs by (job_id, source). Never deletes existing rows.

    - New (job_id, source) pairs are inserted.
    - Matching keys are overwritten in place.
    - Existing JobDescription / AnalysisStatus / Status / Applied values are preserved
      when the incoming values are still defaults.
    - Titles containing Lead / Staff / Principal / Director / Manager are skipped.
    - All other items already in the table are left untouched.
    """
    if not jobs:
        return 0

    # BatchWriteItem rejects duplicate keys in the same request.
    unique_jobs: dict[tuple[str, str], JobListing] = {}
    for job in jobs:
        if is_excluded_title(job.title):
            continue
        unique_jobs[(job.job_id, job.source)] = job

    if not unique_jobs:
        return 0

    table_name = table_name or get_table_name()
    table = get_dynamodb_resource().Table(table_name)
    written = 0

    # put_item only - no delete/clear/recreate of the table.
    with table.batch_writer(overwrite_by_pkeys=[PARTITION_KEY, SORT_KEY]) as batch:
        for job in unique_jobs.values():
            item = job_to_item(job)
            existing = _existing_item(table, job.job_id, job.source)
            if existing:
                incoming_desc = (job.job_description or "").strip()
                if not incoming_desc or incoming_desc == "Not available":
                    existing_desc = existing.get("JobDescription") or existing.get("job_description")
                    if existing_desc and str(existing_desc) != "Not available":
                        item["JobDescription"] = str(existing_desc)

                incoming_analysis = normalize_analysis_status(job.analysis_status)
                item["AnalysisStatus"] = incoming_analysis
                if incoming_analysis == DEFAULT_ANALYSIS_STATUS:
                    existing_analysis = normalize_analysis_status(
                        existing.get("AnalysisStatus")
                        if existing.get("AnalysisStatus") is not None
                        else existing.get("analysis_status")
                    )
                    if existing_analysis != DEFAULT_ANALYSIS_STATUS:
                        item["AnalysisStatus"] = existing_analysis

                incoming_status = normalize_job_status(job.status)
                item["Status"] = incoming_status
                if incoming_status == DEFAULT_JOB_STATUS:
                    existing_status = normalize_job_status(
                        str(
                            existing.get("Status")
                            if existing.get("Status") is not None
                            else existing.get("status")
                            or ""
                        )
                    )
                    if existing_status != DEFAULT_JOB_STATUS:
                        item["Status"] = existing_status

                incoming_applied = (job.applied or "").strip()
                if not incoming_applied or incoming_applied == "No":
                    existing_applied = existing.get("Applied") or existing.get("applied")
                    if existing_applied and str(existing_applied) != "No":
                        item["Applied"] = str(existing_applied)

                if not job.applied_date:
                    existing_applied_date = (
                        existing.get("AppliedDate")
                        or existing.get("applied_date")
                        or existing.get("appliedDate")
                    )
                    if existing_applied_date:
                        item["AppliedDate"] = str(existing_applied_date)

                existing_eval = (
                    existing.get("EvalResult")
                    or existing.get("evalResult")
                    or existing.get("eval_result")
                )
                if existing_eval:
                    item["EvalResult"] = (
                        existing_eval
                        if isinstance(existing_eval, str)
                        else json.dumps(existing_eval)
                    )

            batch.put_item(Item=item)
            written += 1

    return written


def create_job(
    *,
    title: str,
    company: str = "",
    location: str = "",
    url: str = "",
    source: str = "manual",
    table_name: str | None = None,
) -> dict:
    """Create a manually entered job and return the stored record."""
    title = (title or "").strip()
    if not title:
        raise ValueError("title is required")
    if is_excluded_title(title):
        raise ValueError(
            "Titles containing Lead, Staff, Principal, Director, or Manager are not allowed"
        )

    company = (company or "").strip()
    location = (location or "").strip()
    url = (url or "").strip()
    source = (source or "").strip() or "manual"

    job = JobListing(
        title=title,
        company=company,
        location=location,
        date=datetime.now(timezone.utc),
        url=url,
        email_id="",
        source=source,
        job_id=make_job_id(title, company, location),
    )
    put_jobs([job], table_name=table_name)
    return get_job(job.job_id, job.source, table_name=table_name)


def delete_excluded_title_jobs(*, table_name: str | None = None) -> list[dict]:
    """Delete stored jobs whose titles contain Lead / Staff / Principal / Director / Manager.

    Returns the deleted job summaries (jobId, source, title).
    """
    table_name = table_name or get_table_name()
    table = get_dynamodb_resource().Table(table_name)

    items: list[dict] = []
    response = table.scan()
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    deleted: list[dict] = []
    with table.batch_writer() as batch:
        for item in items:
            title = str(item.get("title") or "")
            if not is_excluded_title(title):
                continue
            job_id = item.get(PARTITION_KEY)
            source = item.get(SORT_KEY)
            if not job_id or not source:
                continue
            batch.delete_item(Key={PARTITION_KEY: job_id, SORT_KEY: source})
            deleted.append(
                {
                    "jobId": str(job_id),
                    "source": str(source),
                    "title": title,
                }
            )

    return deleted
