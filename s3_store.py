from __future__ import annotations

import os

import boto3

DEFAULT_BUCKET = "careerpilotai"
DEFAULT_REGION = "us-east-1"

SOURCE_LABELS = {
    "linkedin": "LinkedIn",
    "dice": "Dice",
    "indeed": "Indeed",
    "careerbuilder": "CareerBuilder",
}


def get_bucket_name() -> str:
    return os.getenv("CAREERPILOT_S3_BUCKET", DEFAULT_BUCKET)


def get_s3_client():
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or DEFAULT_REGION
    return boto3.client("s3", region_name=region)


def job_post_key(job_id: str) -> str:
    return f"jobs/{job_id}/job/job_post.txt"


def tailored_resume_key(job_id: str, filename: str) -> str:
    return f"jobs/{job_id}/resume/{filename}"


def build_job_post_text(
    *,
    title: str,
    company: str,
    location: str,
    source: str,
    source_url: str,
    job_description: str,
    employment_type: str = "",
) -> str:
    source_label = SOURCE_LABELS.get(source, source)
    return (
        "=== JOB INFORMATION ===\n"
        f"Title: {title or ''}\n"
        f"Company: {company or ''}\n"
        f"Location: {location or ''}\n"
        f"Employment Type: {employment_type or ''}\n"
        f"Source: {source_label}\n"
        f"Source URL: {source_url or ''}\n"
        "\n"
        "=== JOB DESCRIPTION ===\n"
        f"{job_description or ''}\n"
    )


def upload_job_post(
    *,
    job_id: str,
    title: str,
    company: str,
    location: str,
    source: str,
    source_url: str,
    job_description: str,
    employment_type: str = "",
    bucket: str | None = None,
) -> str:
    """Write jobs/<job_id>/job/job_post.txt and return the object key."""
    bucket = bucket or get_bucket_name()
    key = job_post_key(job_id)
    body = build_job_post_text(
        title=title,
        company=company,
        location=location,
        source=source,
        source_url=source_url,
        job_description=job_description,
        employment_type=employment_type,
    )

    get_s3_client().put_object(
        Bucket=bucket,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="text/plain; charset=utf-8",
    )
    return key


def upload_tailored_resume(
    *,
    job_id: str,
    body: bytes,
    filename: str,
    bucket: str | None = None,
) -> str:
    """Write jobs/<job_id>/resume/<filename> and return the object key."""
    bucket = bucket or get_bucket_name()
    key = tailored_resume_key(job_id, filename)

    get_s3_client().put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    return key


def get_job_description(job_id: str):
    bucket = get_bucket_name()
    key = f"jobs/{job_id}/job/job_post.txt"

    response = get_s3_client().get_object(
        Bucket=bucket,
        Key=key
    )

    text = response["Body"].read().decode("utf-8")

    return text 

