from __future__ import annotations

import config  # noqa: F401 — load .env before AWS / app modules

from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
from io import BytesIO
from starlette.middleware.sessions import SessionMiddleware

from api.admin_auth import (
    AdminStatusResponse,
    admin_status,
    authorization_url,
    clear_admin_session,
    complete_oauth_login,
    get_frontend_url,
    get_session_secret,
    is_admin_request,
    require_admin,
)
from api.demo_jobs import get_demo_job, get_demo_job_description, list_demo_jobs
from api.schemas import Job, JobCreate

from services.cover_letter import generate_cover_letter
from services.fit_check import check_single_job_fit, check_todays_jobs
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
    update_fit,
    update_job_description,
    update_job_status,
)
from fit_status import FIT_STATUSES
from job_status import JOB_STATUSES
from s3_store import (
    get_bucket_name,
    get_job_description as get_s3_job_description,
    get_latest_cover_letter,
    get_latest_tailored_resume,
    upload_job_post,
)
from services.fetch_job_post import JobPostFetchError, fetch_public_job_description

app = FastAPI(title="CareerPilot AI", version="0.1.0")


def _cors_allow_origins() -> list[str]:
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://jobs.ablackcloudapp.com",
        "http://jobs.ablackcloudapp.com",
    ]
    frontend = get_frontend_url()
    if frontend and frontend not in origins:
        origins.append(frontend)
    return origins


_cross_site = get_frontend_url().startswith("https://")

# Session cookie for Google OAuth admin SSO (must be added before routes run).
# Cross-site (S3/CloudFront UI → ALB API) needs SameSite=None + Secure.
app.add_middleware(
    SessionMiddleware,
    secret_key=get_session_secret(),
    session_cookie="careerpilot_session",
    same_site="none" if _cross_site else "lax",
    https_only=_cross_site,
    max_age=60 * 60 * 24 * 14,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Cross-origin UI must read this to use the real .docx download name.
    expose_headers=["Content-Disposition"],
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


class FitCheckTodayRequest(BaseModel):
    force: bool = False
    limit: int | None = Field(default=50, ge=1, le=100)


class FitUpdate(BaseModel):
    source: str = Field(min_length=1)
    fit: Literal["Unset", "Apply", "Maybe", "Skip"]
    reason: str = ""


class FitCheckJobRequest(BaseModel):
    source: str = Field(min_length=1)
    jobDescription: str = ""


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/admin/status", response_model=AdminStatusResponse)
def get_admin_status(request: Request):
    return admin_status(request)


@app.get("/api/admin/login")
def admin_login_start(request: Request):
    """Redirect browser to Google OAuth consent."""
    try:
        url = authorization_url(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OAuth not configured: {exc}") from exc
    return RedirectResponse(url)


@app.get("/api/admin/auth/callback")
def admin_login_callback(request: Request):
    """Google redirects here; establish admin session then return to the UI."""
    if request.query_params.get("error"):
        raise HTTPException(
            status_code=400,
            detail=request.query_params.get("error_description")
            or request.query_params.get("error")
            or "OAuth error",
        )
    # Rebuild the public redirect URL (Vite proxy may rewrite request.url host/port).
    from api.admin_auth import get_oauth_redirect_uri

    authorization_response = f"{get_oauth_redirect_uri()}?{request.url.query}"
    try:
        complete_oauth_login(request, authorization_response=authorization_response)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {exc}") from exc
    return RedirectResponse(f"{get_frontend_url()}/?admin=1")


@app.post("/api/admin/logout")
def admin_logout(request: Request):
    clear_admin_session(request)
    return admin_status(request)


@app.get("/api/jobs")
def get_jobs(request: Request):
    if not is_admin_request(request):
        jobs = list_demo_jobs()
        return {
            "jobs": jobs,
            "count": len(jobs),
            "table": "demo",
            "demo": True,
            "analysisStatuses": list(ANALYSIS_STATUSES),
            "jobStatuses": list(JOB_STATUSES),
            "fitStatuses": list(FIT_STATUSES),
        }

    try:
        jobs = list_jobs()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB read failed: {exc}") from exc

    return {
        "jobs": jobs,
        "count": len(jobs),
        "table": get_table_name(),
        "demo": False,
        "analysisStatuses": list(ANALYSIS_STATUSES),
        "jobStatuses": list(JOB_STATUSES),
        "fitStatuses": list(FIT_STATUSES),
    }


@app.post("/api/jobs")
def post_job(body: JobCreate, _: None = Depends(require_admin)):
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
def get_job_details(job_id: str, source: str, request: Request):
    if not is_admin_request(request):
        try:
            job = get_demo_job(job_id, source)
        except KeyError:
            raise HTTPException(status_code=404, detail="Job Not found") from None
        return {"job": job, "demo": True}

    table_name = get_table_name()
    try:
        job = get_job(job_id, source, table_name=table_name)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job Not found") from None

    return {"job": job, "demo": False}


@app.get("/api/jobs/{job_id}/description")
def read_job_description(job_id: str, source: str, request: Request):
    """Return the full job description text for viewing (no LLM)."""
    source = (source or "").strip()
    if not source:
        raise HTTPException(status_code=400, detail="source is required")

    if not is_admin_request(request):
        try:
            text = get_demo_job_description(job_id, source)
        except KeyError:
            raise HTTPException(status_code=404, detail="Job Not found") from None
        if not text:
            raise HTTPException(status_code=404, detail="Job description not available")
        return {"text": text, "source": "demo"}

    try:
        job = get_job(job_id, source)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB read failed: {exc}") from exc

    marker = (job.get("jobDescription") or "").strip()
    if marker not in ("", "Available", "Not available") and len(marker) >= 40:
        return {"text": marker, "source": "inline"}

    if marker == "Available":
        try:
            text = (get_s3_job_description(job_id) or "").strip()
        except Exception as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Job description file not found: {exc}",
            ) from exc
        if not text:
            raise HTTPException(status_code=404, detail="Job description is empty")
        return {"text": text, "source": "s3"}

    raise HTTPException(status_code=404, detail="Job description not available")


@app.patch("/api/jobs/{job_id}/description")
def patch_job_description(
    job_id: str,
    body: JobDescriptionUpdate,
    _: None = Depends(require_admin),
):
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
def fetch_job_description_from_url(
    job_id: str,
    body: JobDescriptionUpdate,
    _: None = Depends(require_admin),
):
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
def patch_analysis_status(
    job_id: str,
    body: AnalysisStatusUpdate,
    _: None = Depends(require_admin),
):
    try:
        job = update_analysis_status(job_id, body.source, body.analysisStatus)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {exc}") from exc

    return {"job": job}


@app.patch("/api/jobs/{job_id}/status")
def patch_job_status(
    job_id: str,
    body: JobStatusUpdate,
    _: None = Depends(require_admin),
):
    try:
        job = update_job_status(job_id, body.source, body.status)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {exc}") from exc

    return {"job": job}


@app.patch("/api/jobs/{job_id}/applied")
def patch_applied(
    job_id: str,
    body: AppliedUpdate,
    _: None = Depends(require_admin),
):
    try:
        job = update_applied(job_id, body.source, body.applied)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {exc}") from exc

    return {"job": job}


@app.patch("/api/jobs/{job_id}/fit")
def patch_fit(
    job_id: str,
    body: FitUpdate,
    _: None = Depends(require_admin),
):
    try:
        job = update_fit(job_id, body.source, fit=body.fit, reason=body.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {exc}") from exc

    return {"job": job}


@app.post("/api/jobs/fit-check-today")
def post_fit_check_today(
    body: FitCheckTodayRequest | None = None,
    _: None = Depends(require_admin),
):
    payload = body or FitCheckTodayRequest()
    try:
        result = check_todays_jobs(force=payload.force, limit=payload.limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fit check failed: {exc}") from exc
    return result


@app.post("/api/jobs/{job_id}/fit-check")
def post_fit_check_job(
    job_id: str,
    body: FitCheckJobRequest,
    _: None = Depends(require_admin),
):
    """Score fit for one job. Requires a pasted or already-stored job description."""
    try:
        result = check_single_job_fit(
            job_id,
            body.source,
            pasted_description=body.jobDescription or "",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fit check failed: {exc}") from exc
    return result


@app.post("/api/jobs/{job_id}/tailor-resume")
def tailor_resume(job_id: str, body: Job, _: None = Depends(require_admin)):
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
def create_cover_letter(job_id: str, body: Job, _: None = Depends(require_admin)):
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
