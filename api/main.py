from __future__ import annotations

import config  # noqa: F401 — load .env before AWS / app modules

from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from io import BytesIO

from api.schemas import Job, JobCreate

from services.cover_letter import generate_cover_letter
from services.tailor_resume import generate_resume

from analysis_status import ANALYSIS_STATUSES
from dynamodb_store import (
    create_job,
    get_job,
    get_table_name,
    list_jobs,
    update_analysis_status,
    update_applied,
    update_eval_result,
    update_job_description,
    update_job_status,
)
from job_status import JOB_STATUSES
from s3_store import (
    get_bucket_name,
    get_latest_cover_letter,
    get_latest_tailored_resume,
    upload_job_post,
)
from services.fetch_job_post import JobPostFetchError, fetch_public_job_description

app = FastAPI(title="CareerPilot AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AnalysisStatusValue = Literal["Pending", "Tailored Resume", "Cover Letter"]
AppliedValue = Literal["Yes", "No"]
JobStatusValue = Literal[
    "Active",
    "Applied",
    "Interview",
    "Offer",
    "Rejected",
    "Closed",
    "Not Enough Experience",
]


class JobDescriptionUpdate(BaseModel):
    source: str = Field(min_length=1)
    jobDescription: str = ""


class AnalysisStatusUpdate(BaseModel):
    source: str = Field(min_length=1)
    analysisStatus: AnalysisStatusValue


class JobStatusUpdate(BaseModel):
    source: str = Field(min_length=1)
    status: JobStatusValue


class AppliedUpdate(BaseModel):
    source: str = Field(min_length=1)
    applied: AppliedValue


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/jobs")
def get_jobs():
    try:
        jobs = list_jobs()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB read failed: {exc}") from exc

    return {
        "jobs": jobs,
        "count": len(jobs),
        "table": get_table_name(),
        "analysisStatuses": list(ANALYSIS_STATUSES),
        "jobStatuses": list(JOB_STATUSES),
    }


@app.post("/api/jobs")
def post_job(body: JobCreate):
    try:
        job = create_job(
            title=body.title,
            company=body.company,
            location=body.location,
            url=body.url,
            source=body.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB write failed: {exc}") from exc

    pasted = (body.jobDescription or "").strip()
    if pasted:
        try:
            upload_job_post(
                job_id=job["jobId"],
                title=job.get("title", body.title),
                company=job.get("company", body.company),
                location=job.get("location", body.location),
                source=job.get("source", body.source),
                source_url=job.get("url", body.url),
                job_description=pasted,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"S3 upload failed: {exc}") from exc

        try:
            job = update_job_description(job["jobId"], job["source"], "Available")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {exc}") from exc

    return {"job": job}

@app.get("/api/jobs/{job_id}")
def get_job_details(job_id: str, source: str):
    table_name = get_table_name()
    try:
        job = get_job(job_id, source, table_name=table_name)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job Not found")
    
    return {"job": job}


@app.patch("/api/jobs/{job_id}/description")
def patch_job_description(job_id: str, body: JobDescriptionUpdate):
    pasted = (body.jobDescription or "").strip()
    if not pasted:
        raise HTTPException(status_code=400, detail="Job description text is required")

    try:
        job = get_job(job_id, body.source)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB read failed: {exc}") from exc

    # Persist the pasted description as a structured text file in S3.
    try:
        s3_key = upload_job_post(
            job_id=job_id,
            title=job.get("title", ""),
            company=job.get("company", ""),
            location=job.get("location", ""),
            source=job.get("source", body.source),
            source_url=job.get("url", ""),
            job_description=pasted,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {exc}") from exc

    # Mark description as Available only after the S3 file is written.
    try:
        job = update_job_description(job_id, body.source, "Available")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {exc}") from exc

    return {
        "job": job,
        "s3": {
            "bucket": get_bucket_name(),
            "key": s3_key,
        },
    }


@app.post("/api/jobs/{job_id}/description/fetch")
def fetch_job_description_from_url(job_id: str, body: JobDescriptionUpdate):
    """Best-effort: pull description from the job's public URL, save to S3.

    Paste remains the fallback when the page requires login.
    """
    try:
        job = get_job(job_id, body.source)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB read failed: {exc}") from exc

    url = (job.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Job has no URL to fetch")

    try:
        description = fetch_public_job_description(url)
    except JobPostFetchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fetch failed: {exc}") from exc

    try:
        s3_key = upload_job_post(
            job_id=job_id,
            title=job.get("title", ""),
            company=job.get("company", ""),
            location=job.get("location", ""),
            source=job.get("source", body.source),
            source_url=url,
            job_description=description,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {exc}") from exc

    try:
        job = update_job_description(job_id, body.source, "Available")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {exc}") from exc

    return {
        "job": job,
        "fetchedText": description,
        "s3": {
            "bucket": get_bucket_name(),
            "key": s3_key,
        },
    }


@app.patch("/api/jobs/{job_id}/analysis-status")
def patch_analysis_status(job_id: str, body: AnalysisStatusUpdate):
    try:
        job = update_analysis_status(job_id, body.source, body.analysisStatus)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {exc}") from exc

    return {"job": job}


@app.patch("/api/jobs/{job_id}/status")
def patch_job_status(job_id: str, body: JobStatusUpdate):
    try:
        job = update_job_status(job_id, body.source, body.status)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {exc}") from exc

    return {"job": job}


@app.patch("/api/jobs/{job_id}/applied")
def patch_applied(job_id: str, body: AppliedUpdate):
    try:
        job = update_applied(job_id, body.source, body.applied)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {exc}") from exc

    return {"job": job}


@app.post("/api/jobs/{job_id}/tailor-resume")
def tailor_resume(job_id: str, body: Job):
    result = generate_resume(body)
    source = (body.source or "").strip()
    if not source:
        raise HTTPException(status_code=400, detail="source is required")

    try:
        job = update_analysis_status(job_id, source, "Tailored Resume")
        eval_payload = result.get("eval")
        if isinstance(eval_payload, dict):
            job = update_eval_result(job_id, source, eval_payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {exc}") from exc

    return {
        "job": job,
        "s3": {
            "bucket": result.get("bucket"),
            "key": result.get("key"),
        },
        "eval": job.get("evalResult") or result.get("eval"),
    }


@app.get("/api/jobs/{job_id}/tailored-resume")
def download_tailored_resume(job_id: str):
    try:
        _key, body, filename = get_latest_tailored_resume(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"S3 download failed: {exc}") from exc

    return StreamingResponse(
        BytesIO(body),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.post("/api/jobs/{job_id}/cover-letter")
def create_cover_letter(job_id: str, body: Job):
    result = generate_cover_letter(body)
    source = (body.source or "").strip()
    if not source:
        raise HTTPException(status_code=400, detail="source is required")

    try:
        job = update_analysis_status(job_id, source, "Cover Letter")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {exc}") from exc

    return {
        "job": job,
        "s3": {
            "bucket": result.get("bucket"),
            "key": result.get("key"),
            "filename": result.get("filename"),
        },
    }


@app.get("/api/jobs/{job_id}/cover-letter")
def download_cover_letter(job_id: str):
    try:
        _key, body, filename = get_latest_cover_letter(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"S3 download failed: {exc}") from exc

    return StreamingResponse(
        BytesIO(body),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
