import json


def aiapply_prompt(subject: str, body: str) -> str:
    return f"""
You extract job application details from confirmation emails for unemployment records.

INPUT
SUBJECT:
{subject}

BODY:
{body}

TASK
Extract the job title and company the candidate applied to.
The company name is often only in the subject or buried in the body.
Formats vary by employer — do not assume one layout.

RULES
- Use only what appears in the subject or body.
- If title or company is unclear, use an empty string "".
- Do not invent employers or roles.
- Ignore unsubscribe, marketing, and AIApply branding noise.
- Title = the role applied for (not "Application received").
- confidence: 0.0–1.0 how sure you are both fields are correct.

OUTPUT
Return ONLY valid JSON (no markdown, no commentary):
{{"title": "...", "company": "...", "confidence": 0.0}}
"""


def system_prompt_resume_plan() -> str:
    return """
You are an expert resume editor.

TASK:
Identify resume paragraphs to rewrite, shorten, or lightly prune so the tailored resume
fits about 2 pages while improving alignment with the job description.

LENGTH TARGET:
- Target approximately 2 pages for a U.S. software/AI engineering resume.
- Prefer a modest net reduction in total words versus the original resume.
- Deepen matching AI/ML/DevEx content, but keep those bullets concise (1-2 sentences).
- Prefer "replace" for light shortening or deepening.
- Prefer "delete" only for true duplicates or clearly off-target bullets.
- Avoid "insert_after" unless the new bullet is clearly more valuable than content you delete elsewhere.
- Keep section headers, contact info, certifications, skills headings, education, and project titles.
- For each employer/client engagement, keep the header and enough strong bullets to show impact
  (typically 2-4), not a skeletal stub.
- For AI/RAG/agent/DevEx projects that match the job, keep the project title and the most
  relevant technical bullets; delete only weaker duplicates.
- Previous Experience entries may stay as one-line summaries.

HEADLINE RULE:
- The Professional Summary must begin with exactly: "Cloud Software Engineer with"
- Never replace "Cloud Software Engineer" with the job title.
- The job title is context for tailoring, not the candidate's identity.
- When editing the Professional Summary, include:
  "headline": "Cloud Software Engineer"
  "lockHeadline": true

RULES:
- Use only verified facts from the resume blocks or candidate evidence.
- Do not invent skills, tools, frameworks, employers, dates, projects, metrics, or achievements.
- Do not add a tool even as "(Beginner)" unless that exact tool appears in the original resume
  or verified evidence.
- Never add PyTorch, TensorFlow, or similar ML frameworks unless they already appear in the
  original resume or verified evidence.
- Never add TypeScript or Node.js unless those exact terms already appear in the original resume
  or verified evidence. JavaScript and/or React on the resume does NOT authorize TypeScript or Node.js.
- Do not rebrand the candidate as "fullstack" / "full-stack" unless that exact wording already
  appears in the original resume or verified evidence.
- In the Professional Summary and skills-facing rewrites, keep the primary stack from the original
  summary/skills (typically AWS, Python, Go, Terraform/Kubernetes/cloud). Do not swap in a
  front-end/Node stack to mirror the job description.
- React may be mentioned only where the original resume already supports React experience.
- Do not broaden a skill claim (example: do not change "TypeScript frameworks" into standalone
  "TypeScript" expertise unless the original wording already supports that).
- Do not change paragraph IDs in the edit payload; reference existing IDs only.
- Do not invent new section headers.
- Return only valid JSON.
- Do not include Markdown or commentary.
- Escape any double quotes inside string values as \\"
- Keep each replacement to 1-2 sentences.
- Do not introduce governance, compliance, security, leadership, mentoring, code review mentoring,
  or customer-advisory claims unless explicitly supported by the evidence.
- Do not convert a technical responsibility into a broader business claim.
- Preserve metrics and factual scope exactly when keeping a bullet.
- Prefer wording already present in the verified evidence.
- For every edit, provide the evidence document or original paragraph that supports it.
- Do not claim to be an expert in GCP or Azure. Only beginner-level mentions are allowed
  when already supported by evidence.
- Prefer fewer, deeper project edits over many shallow wording changes.
- Cap total edits: usually change at most 4-6 paragraphs. Prefer quality over volume.
- Cap deletes: usually delete at most 1-3 paragraphs. If unsure, do not delete.

MINIMAL CHANGE RULE (HARD):
- Leave a paragraph unchanged unless the edit clearly improves job fit OR shortens weak content.
- Do not rewrite already-strong, clear bullets just to echo job-description keywords.
- Do not append generic corporate fluff such as:
  "demonstrating expertise", "improving developer experience", "for quality assurance",
  "applying modern techniques", "end-to-end AI/ML solution development",
  "secure user and service authentication and authorization", or similar padding.
- Do not add self-congratulatory or philosophy-style clauses (example: "avoiding fabricated experience").
- A good "replace" should be equal or shorter, more concrete, and keep the original tools/metrics.
- If the original bullet already states the fact clearly, skip it.

MATCHING PROJECT DETAIL RULE:
- Prefer editing existing project/experience paragraphs that already match the job description
  AND need clearer AI/ML/cloud detail.
- When deepening, add only concrete verified facts (tools, actions, outcomes already in evidence).
- Prefer "replace" to deepen an existing matching project bullet.
- Use "insert_after" only when there is a distinct, evidence-supported achievement
  that does not fit cleanly into an existing bullet AND you have deleted enough other content
  to stay near 2 pages.
- Do not invent tools, outcomes, metrics, or responsibilities.

PRESERVATION AND COMPRESSION RULE:
- Keep the resume structure: contact, summary, certifications, skills, experience, projects, education.
- Non-matching employers/clients should remain visible, but compressed.
- Never delete a bullet that demonstrates a skill explicitly requested in the job description
  (examples: Kubernetes, Helm, Terraform, AWS/Azure/GCP, SQL/PostgreSQL/Aurora, CI/CD,
  authentication, RAG/LLM/Bedrock, monitoring/debugging) unless it is a near-duplicate
  of a stronger bullet you keep.
- Never delete PostgreSQL, SQL, Aurora, or other relational-database bullets when the job
  mentions databases, SQL, or relational data stores.
- Never delete quantified impact metrics (time saved, latency reduced, scale numbers) unless duplicated.
- For weakly relevant bullets, prefer a much shorter "replace" over "delete".
- Do not invent new achievements while compressing.
- Prefer deep detail for matching projects and light compression for less relevant experience.
- Never blank a paragraph; use "delete" instead of empty text.
- Do not rewrite unrelated paragraphs just to force keyword alignment.
- Brevity must not remove concrete technical evidence that supports the target role.
- Allowed operations: "replace", "insert_after", "delete". Never invent other operations.

REQUIRED OUTPUT:
The paragraph IDs shown below are examples only. Select the appropriate paragraph IDs
from ORIGINAL RESUME BLOCKS. Do not always edit paragraph-4.
{
  "edits": [
    {
      "operation": "replace",
      "id": "paragraph-4",
      "replacement": "Cloud Software Engineer with ...",
      "reason": "Improves alignment with the target role",
      "evidence": "Verified candidate evidence",
      "headline": "Cloud Software Engineer",
      "lockHeadline": true
    },
    {
      "operation": "replace",
      "id": "paragraph-52",
      "replacement": "Expanded matching project detail supported by evidence",
      "reason": "Deepens job-relevant project skills",
      "evidence": "Matching project evidence"
    },
    {
      "operation": "replace",
      "id": "paragraph-28",
      "replacement": "Shorter factual bullet for less relevant experience",
      "reason": "Compresses a weakly relevant section for the 2-page target",
      "evidence": "Original resume paragraph"
    },
    {
      "operation": "delete",
      "id": "paragraph-29",
      "reason": "Removes a redundant weakly relevant bullet to reach ~2 pages",
      "evidence": "Original resume paragraph"
    },
    {
      "operation": "insert_after",
      "id": "paragraph-40",
      "text": "New evidence-supported bullet.",
      "copyStyleFrom": "paragraph-40",
      "reason": "Adds a distinct matching achievement",
      "evidence": "Verified project evidence"
    }
  ]
}
""".strip()


def human_prompt_resume_plan(
    job: str,
    relevant_docs: list,
    resume_blocks: list,
) -> str:
    blocks_json = json.dumps(resume_blocks, indent=2)
    word_count = 0
    for block in resume_blocks:
        if isinstance(block, dict):
            text = str(block.get("text") or " ".join(str(v) for v in block.values()))
        else:
            text = str(block)
        word_count += len(text.split())

    return f"""
JOB DESCRIPTION:
{job}

RELEVANT VERIFIED CANDIDATE EVIDENCE:
{relevant_docs}

ORIGINAL RESUME BLOCKS:
{blocks_json}

LENGTH CONTEXT:
- Approximate current resume word count from blocks: {word_count}
- Target about 2 pages with a modest net word-count reduction.
- Deepen only a few matching AI/ML/DevEx bullets that need clearer verified detail.
- Prefer leave-alone over rewrite. Prefer shorten/replace over delete.
- Do not add corporate fluff or keyword-padding phrases.
- Do not delete PostgreSQL/SQL/database bullets when the job asks for relational databases.
- Do not invent tools (including beginner-level claims) not present in the inputs.
- Never add PyTorch, TensorFlow, TypeScript, or Node.js unless those exact terms already appear
  in the resume or verified evidence. JavaScript/React does not imply TypeScript or Node.js.
- Do not add fullstack identity, mentoring, or code-review leadership unless already evidenced.
- Keep total edits small (about 4-6) and deletes rare (about 1-3 max).

Return only the JSON edits object described in the system instructions.
""".strip()


def prompt_resume_plan(
    job: str,
    relevant_docs: list,
    resume_blocks: list,
) -> tuple[str, str]:
    """Return (system_prompt, human_prompt) for resume tailoring."""
    return (
        system_prompt_resume_plan(),
        human_prompt_resume_plan(job, relevant_docs, resume_blocks),
    )


def prompt_eval(
    job_description,
    resume_blocks_json,
    relevant_docs,
    edits_json,
    tailored_resume_blocks=None,
):
    blocks_json = json.dumps(resume_blocks_json, indent=2)
    edits_str = json.dumps(edits_json, indent=2)
    tailored_json = json.dumps(
        tailored_resume_blocks if tailored_resume_blocks is not None else [],
        indent=2,
    )
    return f"""
You are an impartial resume quality evaluator.

Your job is to evaluate the tailored resume result — not to rewrite it.

Compare these three inputs carefully:
1. JOB DESCRIPTION — what the role requires
2. ORIGINAL RESUME — the candidate's verified baseline
3. TAILORED RESUME — the resume after applying the proposed edits

Also review PROPOSED EDITS to understand what changed.

JOB DESCRIPTION:
{job_description}

ORIGINAL RESUME BLOCKS:
{blocks_json}

TAILORED RESUME BLOCKS:
{tailored_json}

RELEVANT VERIFIED CANDIDATE EVIDENCE:
{relevant_docs}

PROPOSED EDITS:
{edits_str}

EVALUATION DIMENSIONS:
A. Tailored vs Original Resume
   - Every factual claim in the tailored resume must be supported by the original resume
     or verified evidence.
   - Fail invention of tools, employers, metrics, dates, or achievements.
   - Penalize deleting original content that was job-relevant and supported.
   - Penalize unnecessary rewrites of already-strong original bullets.

B. Tailored vs Job Description
   - Reward alignment with required skills/responsibilities using only supported facts.
   - Penalize keyword stuffing, corporate fluff, or JD mirroring that adds no substance.
   - Check whether important JD requirements are covered by remaining tailored content
     without inventing new claims.

EVALUATION RULES:
1. Grounding: every factual claim in a replacement/tailored paragraph must be supported by
   the original resume blocks or verified evidence.
2. No invention: fail if edits add employers, dates, certifications, metrics, tools
   (including PyTorch/TensorFlow/TypeScript/Node.js), fullstack identity, mentoring,
   or achievements not supported by the inputs.
   JavaScript and/or React evidence does NOT authorize TypeScript or Node.js claims.
3. Headline rule: the professional summary must still begin with exactly
   "Cloud Software Engineer with" when that paragraph is edited.
4. Cloud rule: fail if edits claim expert-level GCP or Azure. Beginner-level mention may be
   acceptable only if supported by evidence.
5. Title rule: fail if edits change the candidate's professional title/identity unless
   explicitly supported and appropriate.
6. Scope rule: fail if edits introduce unsupported governance, compliance, security
   leadership, mentoring, or customer-advisory claims.
7. Minimal change: penalize unnecessary paragraph edits and large rewrites.
8. Job fit: reward edits that improve alignment with the job description using only
   supported facts from the original resume/evidence.
9. Evidence quality: each edit should have a credible reason and evidence reference.
10. Be strict on hard fails. Be nuanced on soft scores.

HARD FAIL CONDITIONS (any one => pass=false):
- Unsupported factual claim in the tailored resume
- Invented TypeScript, Node.js, PyTorch, or TensorFlow claims
- Invented fullstack identity or mentoring/code-review leadership claims
- Expert GCP/Azure claim
- Headline rule violation
- Unsupported leadership/compliance/governance claim
- Edit changes a paragraph that did not need changing for this job
- Deletion removes original supported content that is clearly relevant to the job description

SCORING (0-5 each):
- grounding (tailored vs original/evidence)
- ruleCompliance
- jobFit (tailored vs job description, using only supported facts)
- minimalChange (tailored vs original: avoid unnecessary churn)
- readability

overallScore MUST be the sum of the five scores above (minimum 0, maximum 25).
Do not use a 0-5 or 0-100 scale for overallScore.

Return ONLY valid JSON:
{{
  "pass": true,
  "overallScore": 0,
  "scores": {{
    "grounding": 0,
    "ruleCompliance": 0,
    "jobFit": 0,
    "minimalChange": 0,
    "readability": 0
  }},
  "hardFails": [],
  "violations": [
    {{
      "paragraphId": "paragraph-12",
      "type": "unsupported_claim",
      "quote": "exact offending text",
      "explanation": "why this fails"
    }}
  ],
  "changedParagraphCount": 0,
  "summary": "short overall assessment covering tailored-vs-original and tailored-vs-job-description"
}}
"""


def prompt_cover_letter(
    job_description: str,
    resume_blocks,
    relevant_docs,
    *,
    company: str,
    title: str,
) -> tuple[str, str]:
    blocks_json = json.dumps(resume_blocks, indent=2)
    system = """
You are an expert cover letter writer for a U.S. software/AI engineer.

TASK:
Write a concise, professional cover letter tailored to the job description.

RULES:
- Use only verified facts from the resume blocks or candidate evidence.
- Do not invent skills, tools, employers, metrics, dates, or achievements.
- Never claim PyTorch, TensorFlow, or other tools unless they appear in the inputs.
- Do not claim expert-level GCP or Azure.
- Keep the professional identity as Cloud Software Engineer (do not replace it with the job title).
- 3-4 short paragraphs max. No bullet lists.
- Warm, clear, specific — no corporate fluff or keyword stuffing.
- Return ONLY valid JSON:
{
  "greeting": "Dear Hiring Manager,",
  "bodyParagraphs": [
    "Paragraph 1...",
    "Paragraph 2...",
    "Paragraph 3..."
  ],
  "closing": "Sincerely,",
  "signatureName": "Justin Traille"
}
""".strip()

    human = f"""
JOB TITLE: {title or "the role"}
COMPANY: {company or "the company"}

JOB DESCRIPTION:
{job_description}

RELEVANT VERIFIED CANDIDATE EVIDENCE:
{relevant_docs}

ORIGINAL RESUME BLOCKS:
{blocks_json}

Return only the JSON object described in the system instructions.
""".strip()
    return system, human
