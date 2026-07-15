from __future__ import annotations

import os

from dotenv import load_dotenv

from paths import ROOT

load_dotenv(ROOT / ".env")

DEFAULT_AWS_REGION = "us-east-1"
DEFAULT_BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
DEFAULT_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
DEFAULT_RESUME_FILENAME = "Justin_Traille.docx"
DEFAULT_CHROMA_PERSIST_DIR = "chroma_db"
DEFAULT_CHROMA_COLLECTION = "resume-knowledge"


def get_aws_region() -> str:
    return os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or DEFAULT_AWS_REGION


def get_bedrock_model_id() -> str:
    return os.getenv("BEDROCK_MODEL_ID", DEFAULT_BEDROCK_MODEL_ID)


def get_embedding_model_id() -> str:
    return os.getenv("BEDROCK_EMBEDDING_MODEL_ID", DEFAULT_EMBEDDING_MODEL_ID)


def get_resume_filename() -> str:
    return os.getenv("RESUME_FILENAME", DEFAULT_RESUME_FILENAME)


def get_chroma_persist_dir() -> str:
    value = os.getenv("CHROMA_PERSIST_DIR", DEFAULT_CHROMA_PERSIST_DIR)
    path = ROOT / value
    return str(path)


def get_chroma_collection_name() -> str:
    return os.getenv("CHROMA_COLLECTION_NAME", DEFAULT_CHROMA_COLLECTION)
