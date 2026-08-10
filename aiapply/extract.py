from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage

from llm.bedrock.bedrock import llm_service
from llm.prompt.prompt import aiapply_prompt

MIN_CONFIDENCE = 0.5


def parse_extraction_response(response_text: str) -> dict[str, Any]:
    text = (response_text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if "```" in text:
            text = text[: text.rfind("```")].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in extraction response: {text[:300]!r}")

    text = text[start : end + 1]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Extraction model returned invalid JSON. "
            f"Parse error: {exc}. Snippet: {text[max(0, exc.pos - 40) : exc.pos + 40]!r}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError("Extraction response JSON must be an object")
    return payload


def extract_application(subject: str, body: str) -> dict[str, Any]:
    """Call Bedrock to extract title/company/confidence from a confirmation email."""
    llm = llm_service()
    response = llm.invoke([HumanMessage(content=aiapply_prompt(subject, body))])
    payload = parse_extraction_response(response.content)

    title = str(payload.get("title") or "").strip()
    company = str(payload.get("company") or "").strip()
    try:
        confidence = float(payload.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "title": title,
        "company": company,
        "confidence": confidence,
    }


def is_usable_extraction(extracted: dict[str, Any], *, min_confidence: float = MIN_CONFIDENCE) -> bool:
    title = str(extracted.get("title") or "").strip()
    company = str(extracted.get("company") or "").strip()
    try:
        confidence = float(extracted.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return bool(title and company and confidence >= min_confidence)
