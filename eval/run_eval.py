import json

from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, SystemMessage

from config import get_chroma_collection_name, get_chroma_persist_dir
from eval.evaluate import evaluate_edits
from llm.bedrock.bedrock import llm_service
from llm.prompt.prompt import prompt_resume_plan
from llm.rag.embedding import create_embeddings
from llm.rag.load_knowledge import extract_resume_blocks
from paths import ROOT
from services.tailor_resume import parse_resume_edits

CASE_FILE = ROOT / "eval" / "cases" / "01_ai_devex_engineer.json"


def run_eval():
    with CASE_FILE.open(encoding="utf-8") as f:
        data = json.load(f)

    case_id = data.get("id", CASE_FILE.stem)
    full_job_description = data.get("jobDescription")

    current_resume_blocks = extract_resume_blocks()

    embedding = create_embeddings()

    vector_store = Chroma(
        collection_name=get_chroma_collection_name(),
        embedding_function=embedding,
        persist_directory=get_chroma_persist_dir(),
    )

    relevant_docs = vector_store.similarity_search(full_job_description)

    system_prompt, human_prompt = prompt_resume_plan(
        full_job_description, relevant_docs, current_resume_blocks
    )

    llm = llm_service()

    print(f"Running case: {case_id}")
    print("Step 1/2: Tailoring resume...")

    tailor_response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ])
    edits, deletes, _changes = parse_resume_edits(tailor_response.content)

    print(f"  {len(edits)} paragraph(s) replaced, {len(deletes)} deleted")

    print("Step 2/2: Running AI eval...")

    result = evaluate_edits(
        full_job_description,
        current_resume_blocks,
        relevant_docs,
        edits,
        deletes,
    )

    print("\n--- Eval result ---\n")
    print(json.dumps(result, indent=2))
    return result
