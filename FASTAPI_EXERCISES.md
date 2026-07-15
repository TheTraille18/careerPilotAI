# FastAPI practice exercises (CareerPilot AI)

Work through these later using `api/main.py` and related modules.

## 1. Get one job by id

Add `GET /api/jobs/{job_id}?source=linkedin` that returns a single job.

The UI **Full details** page already calls this endpoint. Match this contract:

- Path param: `job_id`
- Query param: `source` (required)
- `200` response body: `{ "job": { ...same fields as list items... } }`
- Return `404` if the job is missing
- You may need a `get_job(job_id, source)` helper in `dynamodb_store.py` (it may already exist)

## 2. Employment type on save

Add `employmentType` to `JobDescriptionUpdate` and include it in the S3 `job_post.txt` under `Employment Type:`.

Hints:
- Extend the Pydantic model in `api/main.py`
- Pass the value into `upload_job_post(...)` / `build_job_post_text(...)`
- Optionally update the UI modal to collect it

## 3. Soft-fail S3 uploads

Change PATCH so if S3 fails, DynamoDB still keeps the description update, but the response includes a warning field (instead of returning 500 for S3 only).

Hints:
- Keep DynamoDB errors as hard failures (404/500)
- Wrap only the S3 call and attach something like `"warning": "S3 upload failed: ..."` when needed

## 4. Use Swagger without the UI

Open http://127.0.0.1:8000/docs and call the Save/description endpoint from Swagger.

Hints:
- Start the API: `uvicorn api.main:app --reload --port 8000`
- Find `PATCH /api/jobs/{job_id}/description`
- Use a real `job_id` + `source` from DynamoDB / the UI

## 5. Tailor Resume POST

The UI **Tailor Resume** button calls this when Job Description is `Available`.

Contract:

- `POST /api/jobs/{job_id}/tailor-resume`
- JSON body: camelCase fields matching the API `Job` model, for example:

```json
{
  "jobId": "...",
  "title": "...",
  "company": "...",
  "location": "...",
  "date": "...",
  "url": "...",
  "source": "linkedin",
  "status": "Active",
  "jobDescription": "Available",
  "analysisStatus": "Pending",
  "applied": "No",
  "emailId": "...",
  "updatedAt": "..."
}
```

- `200` response: `{ "job": { ...same fields as list items... } }`
- `400` if job description is not Available
- `404` if the job is missing

Hints:
- Use `body: Job` on the route
- Path `job_id` should match `body.jobId`
- Check `body.jobDescription == "Available"` before doing work
- For now you can return `{ "job": body.model_dump() }` after validating, then expand later
