"""Load fake jobs for public demo mode (non-admin visitors)."""

from __future__ import annotations

import json
from pathlib import Path

from paths import ROOT

DEMO_JOBS_PATH = ROOT / "data" / "demo" / "jobs.json"


def _load_demo_payload() -> dict:
    if not DEMO_JOBS_PATH.is_file():
        return {"jobs": []}
    data = json.loads(DEMO_JOBS_PATH.read_text())
    if not isinstance(data, dict):
        return {"jobs": []}
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return {"jobs": []}
    return {"jobs": jobs}


def list_demo_jobs() -> list[dict]:
    jobs = list(_load_demo_payload().get("jobs") or [])
    jobs.sort(key=lambda j: str(j.get("date") or ""), reverse=True)
    return jobs


def get_demo_job(job_id: str, source: str) -> dict:
    job_id = (job_id or "").strip()
    source = (source or "").strip()
    for job in list_demo_jobs():
        if str(job.get("jobId") or "") == job_id and str(job.get("source") or "") == source:
            return job
    raise KeyError(f"Demo job not found: {job_id}/{source}")


def get_demo_job_description(job_id: str, source: str) -> str:
    job = get_demo_job(job_id, source)
    text = (job.get("descriptionText") or "").strip()
    if text:
        return text
    marker = (job.get("jobDescription") or "").strip()
    if marker not in ("", "Available", "Not available") and len(marker) >= 40:
        return marker
    return ""
