# CareerPilot AI

Track job listings from email alerts, manage them in a web UI, and tailor your resume to each role using RAG and Amazon Bedrock.

## Features

- **Gmail import** — Parses job alerts from LinkedIn, Dice, Indeed, and CareerBuilder Gmail labels
- **Jobs dashboard** — Filterable table with job details, analysis status, and applied tracking
- **Manual job entry** — Add jobs from the UI with an optional job description
- **Job descriptions** — Paste descriptions in the UI; stored in S3 and marked `Available` in DynamoDB
- **Resume tailoring** — RAG + Claude on Bedrock rewrites resume paragraphs and saves a tailored `.docx` to S3

## Architecture

```
Gmail (labels) ──► gmail.py ──► DynamoDB (job metadata)
                                    │
React UI ◄──► FastAPI ◄─────────────┤
                                    │
                              S3 (job posts + tailored resumes)
                                    │
                              ChromaDB (resume knowledge RAG)
                                    │
                              Amazon Bedrock (embeddings + Claude)
```

| Store | Purpose |
|-------|---------|
| **DynamoDB** | Job metadata (title, company, status, analysis status, etc.) |
| **S3** | `jobs/<job_id>/job/job_post.txt` and `jobs/<job_id>/resume/<filename>` |
| **ChromaDB** | Local vector store for resume knowledge (`./chroma_db`) |

## Prerequisites

- Python 3.11+
- Node.js 18+
- AWS credentials with access to DynamoDB, S3, and Bedrock
- Gmail API credentials (for email import)

## Setup

### 1. Clone and create a virtual environment

```bash
cd careerPilotAI
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install python-docx langchain-aws langchain-chroma langchain-core
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your AWS region, Bedrock model IDs, and optional bucket/table overrides.

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region |
| `CAREERPILOT_JOBS_TABLE` | `careerpilotai_db` | DynamoDB table name |
| `CAREERPILOT_S3_BUCKET` | `careerpilotai` | S3 bucket name |
| `BEDROCK_MODEL_ID` | Claude Sonnet 4.5 | LLM for resume tailoring |
| `BEDROCK_EMBEDDING_MODEL_ID` | Titan Embed Text v2 | Embeddings for RAG |
| `RESUME_FILENAME` | `Justin_Traille.docx` | Base resume in `data/resume/` |
| `CHROMA_PERSIST_DIR` | `chroma_db` | Chroma vector store path |

### 3. Gmail API (optional, for email import)

1. Create a Google Cloud project and enable the Gmail API
2. Download OAuth client credentials as `credentials.json` in the project root
3. Run `python gmail.py` once to complete the browser OAuth flow (`token.json` is created)

Gmail labels used:

| Source | Label |
|--------|-------|
| LinkedIn | `jobs-linkedin` |
| Dice | `jobs-dice` |
| Indeed | `jobs-indeed` |
| CareerBuilder | `Jobs-Careerbuilder` |

### 4. Resume and RAG data

Place your files here:

```
data/
  resume/Justin_Traille.docx    # base resume (or name from RESUME_FILENAME)
  knowledge/*.json              # resume knowledge for RAG (gitignored)
```

Build the vector store:

```bash
python setup_rag.py
```

To reset RAG, delete `chroma_db/` and re-run `setup_rag.py`.

### 5. Frontend

```bash
cd frontend
npm install
```

## Running

Start the API and UI in separate terminals:

```bash
# Terminal 1 — API
source .venv/bin/activate
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — UI
cd frontend
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173).

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Import jobs from Gmail

```bash
source .venv/bin/activate
python gmail.py
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/jobs` | List all jobs |
| `POST` | `/api/jobs` | Create a job manually |
| `GET` | `/api/jobs/{job_id}?source=...` | Get one job |
| `PATCH` | `/api/jobs/{job_id}/description` | Save job description to S3 |
| `PATCH` | `/api/jobs/{job_id}/analysis-status` | Update analysis status |
| `POST` | `/api/jobs/{job_id}/tailor-resume` | Generate a tailored resume |

## Tailor Resume workflow

1. Ensure the job description is **Available** (paste and save in the UI, or include it when adding a job)
2. Click **Tailor Resume** on the job details modal or full-details page
3. The pipeline:
   - Loads the job description from S3
   - Extracts paragraphs from your base resume
   - Retrieves relevant knowledge from Chroma
   - Calls Bedrock Claude to produce paragraph edits
   - Saves the tailored `.docx` to `s3://<bucket>/jobs/<job_id>/resume/`

## Project layout

```
careerPilotAI/
  api/                  # FastAPI routes and schemas
  careerbuilder/        # CareerBuilder email parser
  dice/                 # Dice email parser
  indeed/               # Indeed email parser
  linkedin/             # LinkedIn email parser
  llm/                  # Bedrock client, prompts, RAG helpers
  services/             # tailor_resume pipeline
  frontend/             # React + Vite UI
  data/resume/          # Base resume (.docx)
  data/knowledge/       # RAG knowledge JSON files
  gmail.py              # Gmail import CLI
  setup_rag.py          # Build Chroma vector store
  dynamodb_store.py     # DynamoDB access
  s3_store.py           # S3 access
  config.py             # Environment config (python-dotenv)
```

## Secrets and gitignored files

These files are not committed:

- `.env`
- `credentials.json` / `token.json` (Gmail OAuth)
- `data/knowledge/`
- `chroma_db/`
- `.venv/`, `frontend/node_modules/`

## Learning exercises

See [`FASTAPI_EXERCISES.md`](FASTAPI_EXERCISES.md) for guided backend exercises.
