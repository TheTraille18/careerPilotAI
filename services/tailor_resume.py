import json
import re
from io import BytesIO

from docx import Document
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, SystemMessage

from api.schemas import Job
from config import (
    get_chroma_collection_name,
    get_chroma_persist_dir,
    get_resume_filename,
    get_tailored_resume_filename_prefix,
)
from llm.bedrock.bedrock import llm_service
from llm.prompt.prompt import prompt_resume_plan
from llm.rag.embedding import create_embeddings
from llm.rag.load_knowledge import extract_resume_blocks, iter_resume_paragraphs
from paths import ROOT
from s3_store import get_bucket_name, get_job_description, upload_tailored_resume
from eval.evaluate import evaluate_edits


def _filename_part(value: str, fallback: str) -> str:
    text = re.sub(r"\s+", "_", (value or "").strip())
    text = re.sub(r"[^\w.\-]+", "", text)
    text = re.sub(r"_+", "_", text).strip("._-")
    return text or fallback


def build_tailored_resume_filename(*, company: str, title: str) -> str:
    """Build <TAILORED_RESUME_FILENAME_PREFIX>_<Company>_<Position>.docx."""
    prefix = _filename_part(get_tailored_resume_filename_prefix(), "Tailored_Resume")
    company_part = _filename_part(company, "Company")
    title_part = _filename_part(title, "Position")
    return f"{prefix}_{company_part}_{title_part}.docx"


def delete_paragraph(paragraph) -> None:
    element = paragraph._element
    parent = element.getparent()
    if parent is not None:
        parent.remove(element)


def paragraph_index(paragraph_id: str) -> int | None:
    if not paragraph_id.startswith("paragraph-"):
        return None
    try:
        return int(paragraph_id.split("-", 1)[1])
    except ValueError:
        return None


def apply_resume_edits(
    input_path: str,
    job_id: str,
    edits: dict[str, str],
    uploadFile: bool = True,  # TODO check if this is need for Ai eval
    *,
    deletes: list[str] | None = None,
    output_filename: str | None = None,
) -> str:
    doc = Document(input_path)
    paragraphs = list(iter_resume_paragraphs(doc))

    for index, paragraph in enumerate(paragraphs):
        paragraph_id = f"paragraph-{index}"

        if paragraph_id not in edits:
            continue

        replace_paragraph_text_preserve_style(
            paragraph,
            edits[paragraph_id],
        )

    # Delete after replacements, highest index first so earlier indexes stay stable.
    delete_indexes: list[int] = []
    for paragraph_id in deletes or []:
        index = paragraph_index(paragraph_id)
        if index is not None:
            delete_indexes.append(index)

    for index in sorted(set(delete_indexes), reverse=True):
        if 0 <= index < len(paragraphs):
            delete_paragraph(paragraphs[index])

    filename = output_filename or get_resume_filename().replace(".docx", "_Tailored.docx")
    buffer = BytesIO()
    doc.save(buffer)

    if not uploadFile:
        local_path = ROOT / "data" / "resume" / filename
        local_path.write_bytes(buffer.getvalue())
        return str(local_path)

    return upload_tailored_resume(
        job_id=job_id,
        body=buffer.getvalue(),
        filename=filename,
    )


def replace_paragraph_text_preserve_style(
    paragraph,
    replacement: str,
) -> None:
    if not paragraph.runs:
        paragraph.add_run(replacement)
        return

    paragraph.runs[0].text = replacement

    for run in paragraph.runs[1:]:
        run.text = ""


def parse_resume_edits(
    response_text: str,
) -> tuple[dict[str, str], list[str], list[dict]]:
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if "```" in text:
            text = text[: text.rfind("```")].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in model response: {text[:300]!r}")

    text = text[start : end + 1]

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        # Common when max_tokens cuts the response mid-JSON.
        raise ValueError(
            "Model returned invalid/truncated JSON. "
            "Increase max_tokens or ask for fewer edits. "
            f"Parse error: {exc}. Snippet near error: {text[max(0, exc.pos - 40) : exc.pos + 40]!r}"
        ) from exc

    replacements: dict[str, str] = {}
    deletes: list[str] = []
    changes: list[dict] = []

    for edit in payload.get("edits", []):
        paragraph_id = edit.get("id")
        if not paragraph_id:
            continue

        operation = (edit.get("operation") or "replace").lower()
        reason = str(edit.get("reason") or "").strip()
        evidence = str(edit.get("evidence") or "").strip()

        if operation == "delete":
            deletes.append(paragraph_id)
            changes.append(
                {
                    "paragraphId": paragraph_id,
                    "operation": "delete",
                    "reason": reason,
                    "evidence": evidence,
                    "originalText": "",
                    "newText": "",
                }
            )
            continue

        if operation == "insert_after":
            # Not applied yet; keep parser resilient until insert support lands.
            continue

        replacement = edit.get("replacement")
        if replacement:
            replacements[paragraph_id] = replacement
            changes.append(
                {
                    "paragraphId": paragraph_id,
                    "operation": "replace",
                    "reason": reason,
                    "evidence": evidence,
                    "originalText": "",
                    "newText": replacement,
                }
            )

    return replacements, deletes, changes


def enrich_change_details(resume_blocks, changes: list[dict]) -> list[dict]:
    """Fill originalText for each change from resume blocks."""
    by_id = {
        str(block.get("id")): str(block.get("text") or "")
        for block in (resume_blocks or [])
        if isinstance(block, dict) and block.get("id")
    }
    enriched: list[dict] = []
    for change in changes:
        item = dict(change)
        paragraph_id = str(item.get("paragraphId") or "")
        item["originalText"] = by_id.get(paragraph_id, item.get("originalText") or "")
        enriched.append(item)
    return enriched


def generate_resume(job: Job):
    fullJobDescription = get_job_description(job.jobId)

    currentResumeBlocks = extract_resume_blocks()

    embedding = create_embeddings()

    vector_store = Chroma(
        collection_name=get_chroma_collection_name(),
        embedding_function=embedding,  # same model as ingest
        persist_directory=get_chroma_persist_dir(),
    )

    relevantDocs = vector_store.similarity_search(fullJobDescription)

    system_prompt, human_prompt = prompt_resume_plan(
        fullJobDescription, relevantDocs, currentResumeBlocks
    )

    llm = llm_service()

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ])

    edits, deletes, changes = parse_resume_edits(response.content)
    changes = enrich_change_details(currentResumeBlocks, changes)

    print({"replacements": edits, "deletes": deletes, "changes": len(changes)})

    path = ROOT / "data" / "resume"
    file = get_resume_filename()
    output_filename = build_tailored_resume_filename(
        company=job.company or "",
        title=job.title or "",
    )

    s3_key = apply_resume_edits(
        input_path=f"{path}/{file}",
        job_id=job.jobId,
        edits=edits,
        deletes=deletes,
        output_filename=output_filename,
    )

    print("Running AI eval on tailored edits...")
    try:
        eval_result = evaluate_edits(
            fullJobDescription,
            currentResumeBlocks,
            relevantDocs,
            edits,
            deletes,
        )
    except Exception as exc:
        eval_result = {
            "pass": False,
            "overallScore": 0,
            "scores": {
                "grounding": 0,
                "ruleCompliance": 0,
                "jobFit": 0,
                "minimalChange": 0,
                "readability": 0,
            },
            "hardFails": [f"Eval failed: {exc}"],
            "violations": [],
            "changedParagraphCount": len(edits) + len(deletes),
            "summary": f"Tailoring succeeded, but automatic eval failed: {exc}",
        }

    eval_result["changes"] = changes
    eval_result["changedParagraphCount"] = len(changes)

    return {
        "bucket": get_bucket_name(),
        "key": s3_key,
        "eval": eval_result,
    }
