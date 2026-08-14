from __future__ import annotations

import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from config import get_base_resume_s3_key, get_resume_filename
from paths import ROOT

DEFAULT_BUCKET = "careerpilotai"
DEFAULT_REGION = "us-east-1"

SOURCE_LABELS = {
    "linkedin": "LinkedIn",
    "dice": "Dice",
    "indeed": "Indeed",
    "careerbuilder": "CareerBuilder",
    "remoterocketship": "Remote Rocketship",
    "aiapply": "AIApply",
}


def get_bucket_name() -> str:
    return os.getenv("CAREERPILOT_S3_BUCKET", DEFAULT_BUCKET)


def get_s3_client():
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or DEFAULT_REGION
    return boto3.client("s3", region_name=region)


def local_base_resume_path() -> Path:
    return ROOT / "data" / "resume" / get_resume_filename()


def load_base_resume_bytes() -> bytes:
    """Load the base resume from S3; fall back to ``data/resume/`` if missing."""
    bucket = get_bucket_name()
    key = get_base_resume_s3_key()
    try:
        response = get_s3_client().get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
    except ClientError:
        local = local_base_resume_path()
        if local.is_file():
            return local.read_bytes()
        raise FileNotFoundError(
            f"Base resume not found in s3://{bucket}/{key} or at {local}"
        ) from None


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


def list_resume_dir_objects(job_id: str, *, bucket: str | None = None) -> list[dict]:
    """List objects under jobs/<job_id>/resume/."""
    bucket = bucket or get_bucket_name()
    prefix = f"jobs/{job_id}/resume/"
    client = get_s3_client()
    objects: list[dict] = []
    token: str | None = None

    while True:
        kwargs: dict = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        response = client.list_objects_v2(**kwargs)
        for item in response.get("Contents", []):
            key = item.get("Key") or ""
            if key.endswith("/") or key == prefix:
                continue
            objects.append(item)
        if not response.get("IsTruncated"):
            break
        token = response.get("NextContinuationToken")

    return objects


def list_tailored_resume_objects(job_id: str, *, bucket: str | None = None) -> list[dict]:
    """List resume objects under jobs/<job_id>/resume/ (excludes cover letters)."""
    return [
        item
        for item in list_resume_dir_objects(job_id, bucket=bucket)
        if not str(item.get("Key") or "").rsplit("/", 1)[-1].startswith("Cover_Letter_")
    ]


def _download_latest_matching(
    job_id: str,
    *,
    objects: list[dict],
    missing_message: str,
    bucket: str | None = None,
) -> tuple[str, bytes, str]:
    if not objects:
        raise FileNotFoundError(missing_message)
    bucket = bucket or get_bucket_name()
    latest = max(objects, key=lambda item: item.get("LastModified") or 0)
    key = str(latest["Key"])
    filename = key.rsplit("/", 1)[-1] or "document.docx"
    response = get_s3_client().get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()
    return key, body, filename


def get_latest_tailored_resume(
    job_id: str,
    *,
    bucket: str | None = None,
) -> tuple[str, bytes, str]:
    """Return (key, body, filename) for the newest tailored resume, or raise FileNotFoundError."""
    return _download_latest_matching(
        job_id,
        objects=list_tailored_resume_objects(job_id, bucket=bucket),
        missing_message=f"No tailored resume found for job {job_id}",
        bucket=bucket,
    )


def get_latest_cover_letter(
    job_id: str,
    *,
    bucket: str | None = None,
) -> tuple[str, bytes, str]:
    """Return (key, body, filename) for the newest cover letter, or raise FileNotFoundError."""
    objects = [
        item
        for item in list_resume_dir_objects(job_id, bucket=bucket)
        if str(item.get("Key") or "").rsplit("/", 1)[-1].startswith("Cover_Letter_")
    ]
    return _download_latest_matching(
        job_id,
        objects=objects,
        missing_message=f"No cover letter found for job {job_id}",
        bucket=bucket,
    )

