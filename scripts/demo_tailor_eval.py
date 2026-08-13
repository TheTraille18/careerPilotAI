#!/usr/bin/env python3
"""Run resume tailor + AI eval on demo jobs and persist evalResult into the JSON.

Uses Bedrock (costs money). Skips S3 upload for tailored docs.
"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: F401 — load .env

from api.schemas import Job
from paths import ROOT as APP_ROOT
from services import tailor_resume as tr

DEMO_PATH = APP_ROOT / "data" / "demo" / "jobs.json"


def main() -> int:
    data = json.loads(DEMO_PATH.read_text())
    jobs: list[dict] = list(data.get("jobs") or [])
    by_id = {
        (str(j.get("jobId") or ""), str(j.get("source") or "")): j
        for j in jobs
    }
    desc_by_id = {
        str(j.get("jobId") or ""): (j.get("descriptionText") or "").strip()
        for j in jobs
        if (j.get("descriptionText") or "").strip()
    }

    targets = [
        j
        for j in jobs
        if (j.get("descriptionText") or "").strip()
        and (j.get("jobDescription") or "").strip() == "Available"
    ]
    print(f"Demo jobs with JD text: {len(targets)} / {len(jobs)}", flush=True)

    # Serve demo JD text instead of S3.
    tr.get_job_description = lambda job_id: desc_by_id.get(str(job_id), "")

    original_apply = tr.apply_resume_edits

    def apply_local(*args, **kwargs):
        kwargs["uploadFile"] = False
        return original_apply(*args, **kwargs)

    tr.apply_resume_edits = apply_local

    ok = 0
    failed = 0
    for index, job in enumerate(targets, start=1):
        job_id = str(job.get("jobId") or "")
        source = str(job.get("source") or "")
        title = job.get("title") or job_id
        print(f"\n[{index}/{len(targets)}] Tailor+eval: {title} ({job_id})", flush=True)
        try:
            payload = Job(
                jobId=job_id,
                title=job.get("title") or "",
                company=job.get("company") or "",
                location=job.get("location") or "",
                date=job.get("date") or "",
                url=job.get("url") or "",
                source=source,
                status=job.get("status") or "Active",
                jobDescription="Available",
                analysisStatus=job.get("analysisStatus") or "Pending",
                applied=job.get("applied") or "No",
                appliedDate=job.get("appliedDate") or "",
                emailId=job.get("emailId") or "",
                updatedAt=job.get("updatedAt") or "",
            )
            result = tr.generate_resume(payload)
            eval_result = result.get("eval")
            if not isinstance(eval_result, dict):
                raise RuntimeError("No eval payload returned")
            eval_result["evaluatedAt"] = datetime.now(timezone.utc).isoformat()

            target = by_id[(job_id, source)]
            target["evalResult"] = eval_result
            target["analysisStatus"] = "Tailored Resume"
            target["updatedAt"] = datetime.now(timezone.utc).isoformat()
            DEMO_PATH.write_text(json.dumps(data, indent=2) + "\n")
            ok += 1
            score = eval_result.get("overallScore")
            passed = eval_result.get("pass")
            print(f"  OK — pass={passed} overallScore={score}", flush=True)
        except Exception as exc:
            failed += 1
            print(f"  FAIL — {exc}", flush=True)
            traceback.print_exc()

    print(f"\nDone. ok={ok} failed={failed}", flush=True)
    print(f"Wrote: {DEMO_PATH}", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
