from __future__ import annotations

import os

from dotenv import load_dotenv

from paths import ROOT

load_dotenv(ROOT / ".env")

DEFAULT_AWS_REGION = "us-east-1"
DEFAULT_BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
DEFAULT_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
DEFAULT_RESUME_FILENAME = "Justin_Traille.docx"
DEFAULT_TAILORED_RESUME_FILENAME_PREFIX = "Justin_Traille"
DEFAULT_CHROMA_PERSIST_DIR = "chroma_db"
DEFAULT_CHROMA_COLLECTION = "resume-knowledge"
DEFAULT_LOCAL_TIMEZONE = "America/New_York"


def get_aws_region() -> str:
    return os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or DEFAULT_AWS_REGION


def get_bedrock_model_id() -> str:
    return os.getenv("BEDROCK_MODEL_ID", DEFAULT_BEDROCK_MODEL_ID)


def get_embedding_model_id() -> str:
    return os.getenv("BEDROCK_EMBEDDING_MODEL_ID", DEFAULT_EMBEDDING_MODEL_ID)


def get_resume_filename() -> str:
    return os.getenv("RESUME_FILENAME", DEFAULT_RESUME_FILENAME)


def get_tailored_resume_filename_prefix() -> str:
    return os.getenv(
        "TAILORED_RESUME_FILENAME_PREFIX",
        DEFAULT_TAILORED_RESUME_FILENAME_PREFIX,
    )


def get_local_timezone_name() -> str:
    return os.getenv("CAREERPILOT_TIMEZONE", DEFAULT_LOCAL_TIMEZONE)


def get_local_today_iso() -> str:
    """Return today's calendar date in the configured local timezone (YYYY-MM-DD)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo(get_local_timezone_name())).date().isoformat()


def get_chroma_persist_dir() -> str:
    value = os.getenv("CHROMA_PERSIST_DIR", DEFAULT_CHROMA_PERSIST_DIR)
    path = ROOT / value
    return str(path)


def get_chroma_collection_name() -> str:
    return os.getenv("CHROMA_COLLECTION_NAME", DEFAULT_CHROMA_COLLECTION)
