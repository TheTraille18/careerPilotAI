from __future__ import annotations

import config  # noqa: F401 — load .env before AWS / app modules

from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.schemas import Job, JobCreate

from services.tailor_resume import generate_resume

from analysis_status import ANALYSIS_STATUSES
from dynamodb_store import (
    create_job,
    get_job,
    get_table_name,
    list_jobs,
    update_analysis_status,
    update_job_description,
)
from s3_store import get_bucket_name, upload_job_post

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

AnalysisStatusValue = Literal["Pending", "In_Progress", "Completed", "Failed", "Retry"]


class JobDescriptionUpdate(BaseModel):
    source: str = Field(min_length=1)
    jobDescription: str = ""


class AnalysisStatusUpdate(BaseModel):
    source: str = Field(min_length=1)
    analysisStatus: AnalysisStatusValue


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


@app.patch("/api/jobs/{job_id}/analysis-status")
def patch_analysis_status(job_id: str, body: AnalysisStatusUpdate):
    try:
        job = update_analysis_status(job_id, body.source, body.analysisStatus)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {exc}") from exc

    return {"job": job}


@app.post("/api/jobs/{job_id}/tailor-resume")
def tailor_resume(job_id: str, body: Job):
    s3 = generate_resume(body)
    return {"job": body.model_dump(), "s3": s3}
