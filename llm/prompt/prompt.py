import json

def prompt_resume_plan(job: str, relevant_docs: list, resume_blocks: list) -> str:
        blocks_json = json.dumps(resume_blocks, indent= 2)
        return f"""
You are an expert resume editor.

JOB DESCRIPTION:
{job}

RELEVANT VERIFIED CANDIDATE EVIDENCE:
{relevant_docs}

ORIGINAL RESUME BLOCKS:
{blocks_json}

TASK:
Identify only the resume paragraphs that should be rewritten to improve
alignment with the job description.

The first sentence of the Professional Summary must begin with exactly:

Cloud Software Engineer with

Do not modify those first four words.

RULES:
- Use only verified facts from the resume blocks or candidate evidence.
- Do not invent skills, employers, dates, projects, or achievements.
- Do not change paragraph IDs.
- Do not add or remove sections.
- Preserve the purpose and approximate length of each paragraph.
- Return only valid JSON.
- Do not include Markdown or commentary.
- Escape any double quotes inside string values as \\"
- Keep the edits array small: only paragraphs that must change.
- Keep each replacement to 1-3 sentences.
- Do not change the candidate's professional title unless the job title
  directly matches verified past experience.
- Do not introduce governance, compliance, security, leadership, mentoring,
  or customer-advisory claims unless explicitly supported by the evidence.
- Do not convert a technical responsibility into a broader business claim.
- Preserve metrics and factual scope exactly.
- Prefer wording already present in the verified evidence.
- For every replacement, provide the evidence document or original paragraph
  that supports it.
- Do not make mention being an expert in GCP nor Azure. Only a beginner in those 2
- Do not change the candidate's professional title or identity unless explicitly instructed.
- The resume headline should remain "Cloud Software Engineer" unless the user requests otherwise.
- You may tailor the professional summary to emphasize the most relevant experience for the job description.

REQUIRED OUTPUT:
{{
  "edits": [
    {{
      "id": "paragraph-12",
      "replacement": "Rewritten text",
      "reason": "Matches application modernization requirement",
      "evidence": "Capital One Aurora migration document",
      "headline": "Cloud Software Engineer",
      "lockHeadline": true
    }}
  ]
}}
"""