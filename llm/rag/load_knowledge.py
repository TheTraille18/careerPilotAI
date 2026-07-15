import json

from docx import Document

from config import get_resume_filename
from paths import ROOT


def load_knowledge_files() -> list:
    path = ROOT / "data" / "knowledge"

    knowledge: list = []


    for file in sorted(path.glob("*.json")):
        with file.open(encoding="utf-8") as f:
            knowledge.append(json.load(f))

    return(knowledge)

def extract_resume_blocks() -> list:
    path = ROOT / "data" / "resume"
    file = get_resume_filename()
    blocks = []
    
    doc = Document(f"{path}/{file}")

    for index, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()

        if not text:
            continue

        blocks.append({
            "id": f"paragraph-{index}",
            "text": text,
            "style": paragraph.style.name if paragraph.style else "",
        })

    return blocks