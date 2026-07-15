import json
from io import BytesIO

from docx import Document
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage

from api.schemas import Job
from config import get_chroma_collection_name, get_chroma_persist_dir, get_resume_filename
from llm.bedrock.bedrock import llm_service
from llm.prompt.prompt import prompt_resume_plan
from llm.rag.embedding import create_embeddings
from llm.rag.load_knowledge import extract_resume_blocks
from paths import ROOT
from s3_store import get_bucket_name, get_job_description, upload_tailored_resume


def apply_resume_edits(
    input_path: str,
    job_id: str,
    edits: dict[str, str],
    *,
    output_filename: str | None = None,
) -> str:
    doc = Document(input_path)

    for index, paragraph in enumerate(doc.paragraphs):
        paragraph_id = f"paragraph-{index}"

        if paragraph_id not in edits:
            continue

        replace_paragraph_text_preserve_style(
            paragraph,
            edits[paragraph_id],
        )

    filename = output_filename or get_resume_filename().replace(".docx", "_Tailored.docx")
    buffer = BytesIO()
    doc.save(buffer)

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

def parse_resume_edits(response_text: str) -> dict[str, str]:
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

    edits: dict[str, str] = {}
    for edit in payload.get("edits", []):
        paragraph_id = edit.get("id")
        replacement = edit.get("replacement")
        if paragraph_id and replacement:
            edits[paragraph_id] = replacement

    return edits


def generate_resume(job: Job):
    
    fullJobDescription = get_job_description(job.jobId)

  
    currentResumeBlocks = extract_resume_blocks()

    embedding = create_embeddings()

    vector_store = Chroma(
        collection_name=get_chroma_collection_name(),
        embedding_function=embedding,   # same model as ingest
        persist_directory=get_chroma_persist_dir(),
    )

    relevantDocs = vector_store.similarity_search(fullJobDescription)


    prompt = prompt_resume_plan(fullJobDescription, relevantDocs, currentResumeBlocks)

    llm = llm_service()

    response = llm.invoke([
        HumanMessage(content=prompt),
    ])

    edits = parse_resume_edits(response.content)

    print(edits)

    path = ROOT / "data" / "resume"
    file = get_resume_filename()

    s3_key = apply_resume_edits(
        input_path=f"{path}/{file}",
        job_id=job.jobId,
        edits=edits,
    )

    return {
        "bucket": get_bucket_name(),
        "key": s3_key,
    }

    




