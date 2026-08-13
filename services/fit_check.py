from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.messages import HumanMessage, SystemMessage

from config import get_local_timezone_name, get_local_today_iso
from dynamodb_store import get_job, list_jobs, update_fit, update_job_description
from fit_status import DEFAULT_FIT_STATUS, normalize_fit_status
from llm.bedrock.bedrock import llm_service
from paths import ROOT
from s3_store import get_job_description, upload_job_post
from services.fetch_job_post import JobPostFetchError, fetch_public_job_description

KNOWLEDGE_DIR = ROOT / "data" / "knowledge"

CANDIDATE_FALLBACK = """
Candidate: Justin Traille
Target: AI / cloud / platform / agent roles first; strong cloud engineering as backup.
Strengths: AWS, Terraform/IaC, Kubernetes, Python, Go, CI/CD, automation, platform engineering;
building AI agents, MCP tools, RAG, LangChain/tool-calling side projects (CareerPilot AI, KubeSentryAI, ai-assistant).
Experience level: mid-level IC (~4–8 years range) — NOT a 12–15 year / principal hire.
Weaker / rusty: Java/Spring full-stack, heavy React/Next.js frontend ownership, pure research/edge ML (NPU/quantization), C#.
Prefer Atlanta / hybrid / remote. Avoid Lead/Staff/Principal/Director/Manager titles when clearly senior-mgmt.
""".strip()


def _load_profile_snippet() -> str:
    parts: list[str] = [CANDIDATE_FALLBACK]
    for name in ("ProfessionalSummary.json", "TechnicalSkills.json"):
        path = KNOWLEDGE_DIR / name
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        parts.append(f"### {name}\n{json.dumps(payload, indent=2)[:4000]}")
    return "\n\n".join(parts)


def _job_local_date(job: dict) -> str | None:
    raw = (job.get("date") or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
            return raw[:10]
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo(get_local_timezone_name())).date().isoformat()


def _parse_fit_response(response_text: str) -> dict:
    text = (response_text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if "```" in text:
            text = text[: text.rfind("```")].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object in fit response: {text[:300]!r}")

    payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("Fit response JSON must be an object")

    fit = normalize_fit_status(str(payload.get("fit") or ""))
    if fit == DEFAULT_FIT_STATUS:
        fit = "Maybe"
    reason = str(payload.get("reason") or "").strip() or "No reason provided."
    return {"fit": fit, "reason": reason[:500]}


def _looks_like_inline_description(value: str) -> bool:
    text = (value or "").strip()
    return bool(text) and text not in {"Not available", "Available"}


def resolve_job_description(job: dict) -> tuple[str | None, str]:
    """Return (description_text, source_label).

    Order: inline Dynamo text → S3 when Available → fetch public URL (persist on success).
    """
    job_id = (job.get("jobId") or "").strip()
    source = (job.get("source") or "").strip()
    marker = (job.get("jobDescription") or "").strip()

    if _looks_like_inline_description(marker):
        return marker, "inline"

    if marker == "Available" and job_id:
        try:
            text = (get_job_description(job_id) or "").strip()
            if len(text) >= 40:
                return text, "s3"
        except Exception:
            pass

    url = (job.get("url") or "").strip()
    if not url:
        return None, "none"

    try:
        text = fetch_public_job_description(url)
    except JobPostFetchError:
        return None, "fetch_failed"
    except Exception:
        return None, "fetch_failed"

    text = (text or "").strip()
    if len(text) < 40:
        return None, "fetch_failed"

    # Persist for Career Pilot UI + future fit runs.
    if job_id and source:
        try:
            upload_job_post(
                job_id=job_id,
                title=job.get("title") or "",
                company=job.get("company") or "",
                location=job.get("location") or "",
                source=source,
                source_url=url,
                job_description=text,
            )
            update_job_description(job_id, source, "Available")
            job["jobDescription"] = "Available"
        except Exception:
            # Scoring can still use the fetched text even if persist fails.
            pass

    return text, "fetched"


def evaluate_job_fit(
    job: dict,
    *,
    profile: str | None = None,
    description: str | None = None,
    description_source: str = "none",
) -> dict:
    profile_text = profile or _load_profile_snippet()
    has_description = bool(description and len(description.strip()) >= 40)
    if has_description:
        desc_block = description.strip()
    else:
        desc_block = (
            "(No full job description available after S3/URL lookup — "
            "score conservatively from title/company/location/url only. "
            "Do NOT return Apply without a real JD; use Maybe or Skip.)"
        )

    system = (
        "You are a job-fit assistant for Justin Traille's job search. "
        "Prefer AI/agent/LLM/RAG/platform roles, then strong AWS/cloud/K8s/devops. "
        "Be honest about weak Java/Spring/React-heavy full-stack or research ML mismatches. "
        "If the JD requires ~10+ or 12–15 years / principal-level depth, return Skip "
        "(candidate is mid-level IC, not that band). "
        "If no real job description is provided, never return Apply. "
        "Respond with ONLY compact JSON: "
        '{"fit":"Apply"|"Maybe"|"Skip","reason":"one short sentence"}'
    )
    human = (
        f"Candidate profile:\n{profile_text}\n\n"
        f"Description source: {description_source}\n"
        f"Has full JD: {has_description}\n"
        f"Job title: {job.get('title') or ''}\n"
        f"Company: {job.get('company') or ''}\n"
        f"Location: {job.get('location') or ''}\n"
        f"Source: {job.get('source') or ''}\n"
        f"URL: {job.get('url') or ''}\n"
        f"Description:\n{desc_block[:8000]}\n"
    )

    llm = llm_service()
    response = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=human),
        ]
    )
    content = response.content
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in content
        )
    verdict = _parse_fit_response(str(content))

    # Hard guard: never persist Apply without a real JD.
    if not has_description and verdict["fit"] == "Apply":
        verdict["fit"] = "Maybe"
        verdict["reason"] = (
            f"{verdict['reason']} (Downgraded to Maybe: no job description fetched.)"
        )[:500]

    return verdict


def check_todays_jobs(*, force: bool = False, limit: int | None = 50) -> dict:
    """Evaluate fit for jobs whose email date is today (local TZ). Persist FitFlag."""
    today = get_local_today_iso()
    jobs = list_jobs()
    todays = [job for job in jobs if _job_local_date(job) == today]
    if limit is not None:
        todays = todays[: max(0, int(limit))]

    profile = _load_profile_snippet()
    results: list[dict] = []
    evaluated = 0
    skipped_existing = 0
    with_description = 0
    errors: list[dict] = []

    for job in todays:
        job_id = job.get("jobId") or ""
        source = job.get("source") or ""
        existing = normalize_fit_status(job.get("fit"))
        if not force and existing != DEFAULT_FIT_STATUS:
            skipped_existing += 1
            results.append(
                {
                    "jobId": job_id,
                    "source": source,
                    "title": job.get("title"),
                    "fit": existing,
                    "reason": job.get("fitReason") or "",
                    "skipped": True,
                    "descriptionSource": "skipped",
                }
            )
            continue

        try:
            description, desc_source = resolve_job_description(job)
            if description:
                with_description += 1
            verdict = evaluate_job_fit(
                job,
                profile=profile,
                description=description,
                description_source=desc_source,
            )
            updated = update_fit(
                job_id,
                source,
                fit=verdict["fit"],
                reason=verdict["reason"],
            )
            evaluated += 1
            results.append(
                {
                    "jobId": job_id,
                    "source": source,
                    "title": job.get("title"),
                    "fit": updated.get("fit"),
                    "reason": updated.get("fitReason"),
                    "skipped": False,
                    "descriptionSource": desc_source,
                }
            )
        except Exception as exc:  # noqa: BLE001 — collect per-job failures for UI
            errors.append(
                {
                    "jobId": job_id,
                    "source": source,
                    "title": job.get("title"),
                    "error": str(exc),
                }
            )

    return {
        "date": today,
        "candidateCount": len(todays),
        "evaluated": evaluated,
        "withDescription": with_description,
        "skippedExisting": skipped_existing,
        "errorCount": len(errors),
        "results": results,
        "errors": errors,
    }


def check_single_job_fit(
    job_id: str,
    source: str,
    *,
    pasted_description: str = "",
) -> dict:
    """Evaluate one job. Requires pasted text or an already-stored description (S3/inline).

    Does not fetch from URL here — user must paste or have Available/inline JD.
    """
    job = get_job(job_id, source)
    pasted = (pasted_description or "").strip()

    description: str | None = None
    desc_source = "none"

    if pasted:
        # Persist paste so Career Pilot keeps the JD.
        upload_job_post(
            job_id=job_id,
            title=job.get("title") or "",
            company=job.get("company") or "",
            location=job.get("location") or "",
            source=source,
            source_url=job.get("url") or "",
            job_description=pasted,
        )
        job = update_job_description(job_id, source, "Available")
        description = pasted
        desc_source = "pasted"
    else:
        marker = (job.get("jobDescription") or "").strip()
        if _looks_like_inline_description(marker):
            description = marker
            desc_source = "inline"
        elif marker == "Available":
            try:
                text = (get_job_description(job_id) or "").strip()
            except Exception as exc:
                raise ValueError(
                    "Job is marked Available but description could not be loaded from S3"
                ) from exc
            if len(text) < 40:
                raise ValueError("Stored job description is empty — paste the JD first")
            description = text
            desc_source = "s3"
        else:
            raise ValueError(
                "No job description yet — paste one or fetch/save a description first"
            )

    verdict = evaluate_job_fit(
        job,
        description=description,
        description_source=desc_source,
    )
    updated = update_fit(
        job_id,
        source,
        fit=verdict["fit"],
        reason=verdict["reason"],
    )
    return {
        "job": updated,
        "fit": updated.get("fit"),
        "reason": updated.get("fitReason"),
        "descriptionSource": desc_source,
    }
