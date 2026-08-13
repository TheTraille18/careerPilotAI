from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage

from llm.bedrock.bedrock import llm_service
from llm.prompt.prompt import prompt_eval


def parse_eval_response(response_text: str) -> dict[str, Any]:
    text = (response_text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if "```" in text:
            text = text[: text.rfind("```")].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in eval response: {text[:300]!r}")

    text = text[start : end + 1]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Eval model returned invalid/truncated JSON. "
            f"Parse error: {exc}. Snippet: {text[max(0, exc.pos - 40) : exc.pos + 40]!r}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError("Eval response JSON must be an object")
    return normalize_eval_scores(payload)


def normalize_eval_scores(payload: dict[str, Any]) -> dict[str, Any]:
    """Force overallScore to the sum of the five 0-5 dimension scores when present."""
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        return payload

    keys = ("grounding", "ruleCompliance", "jobFit", "minimalChange", "readability")
    total = 0
    have_all = True
    for key in keys:
        value = scores.get(key)
        if not isinstance(value, (int, float)):
            have_all = False
            break
        total += int(value)
    if have_all:
        payload["overallScore"] = total
    return payload


def build_tailored_resume_blocks(
    resume_blocks,
    edits: dict[str, str],
    deletes: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Apply replacements/deletes to original resume blocks for eval comparison."""
    delete_set = set(deletes or [])
    tailored: list[dict[str, Any]] = []

    for block in resume_blocks or []:
        if not isinstance(block, dict):
            continue
        paragraph_id = str(block.get("id") or "")
        if paragraph_id in delete_set:
            continue

        text = edits.get(paragraph_id, block.get("text", ""))
        tailored.append(
            {
                "id": paragraph_id,
                "text": text,
                "style": block.get("style", ""),
                "changed": paragraph_id in edits,
            }
        )

    return tailored


def evaluate_edits(
    job_description: str,
    resume_blocks,
    relevant_docs,
    edits: dict[str, str],
    deletes: list[str] | None = None,
) -> dict[str, Any]:
    """Evaluate tailored resume vs job description and vs original resume."""
    deletes = deletes or []
    tailored_blocks = build_tailored_resume_blocks(resume_blocks, edits, deletes)
    eval_prompt = prompt_eval(
        job_description,
        resume_blocks,
        relevant_docs,
        {"replacements": edits, "deletes": deletes},
        tailored_resume_blocks=tailored_blocks,
    )
    llm = llm_service()
    eval_response = llm.invoke([HumanMessage(content=eval_prompt)])
    return parse_eval_response(eval_response.content)
