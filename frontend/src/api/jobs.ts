import type { AnalysisStatus, JobListing, JobsResponse } from '../types/job';

export type JobCreateInput = {
  title: string;
  company?: string;
  location?: string;
  url?: string;
  source?: string;
  jobDescription?: string;
};

export async function createJob(input: JobCreateInput): Promise<JobListing> {
  const response = await fetch('/api/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: input.title,
      company: input.company ?? '',
      location: input.location ?? '',
      url: input.url ?? '',
      source: input.source ?? 'manual',
      jobDescription: input.jobDescription ?? '',
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  const data = (await response.json()) as { job: JobListing };
  return data.job;
}

export async function fetchJobs(): Promise<JobsResponse> {
  const response = await fetch('/api/jobs');
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  return response.json() as Promise<JobsResponse>;
}

/**
 * Exercise 1 contract (implement the FastAPI route yourself):
 *   GET /api/jobs/{job_id}?source=<source>
 *   200 -> { "job": { ...JobListing fields... } }
 *   404 when the job is missing
 */
export async function fetchJob(jobId: string, source: string): Promise<JobListing> {
  const params = new URLSearchParams({ source });
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}?${params}`);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  const data = (await response.json()) as { job: JobListing };
  return data.job;
}

export async function updateJobDescription(
  jobId: string,
  source: string,
  jobDescription: string,
): Promise<JobListing> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/description`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, jobDescription }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  const data = (await response.json()) as { job: JobListing };
  return data.job;
}

export async function updateAnalysisStatus(
  jobId: string,
  source: string,
  analysisStatus: AnalysisStatus,
): Promise<JobListing> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/analysis-status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, analysisStatus }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  const data = (await response.json()) as { job: JobListing };
  return data.job;
}

/**
 * Tailor Resume contract (implement the FastAPI route yourself):
 *   POST /api/jobs/{job_id}/tailor-resume
 *   body: full job object matching api Job (camelCase)
 *   200 -> { "job": { ...JobListing fields... }, "s3": { "bucket", "key" } }
 *   400 if job description is not Available
 *   404 when the job is missing
 */
export type TailorResumeResponse = {
  job: JobListing;
  s3?: {
    bucket: string;
    key: string;
  };
};

export function formatTailorSuccessMessage(s3?: TailorResumeResponse['s3']): string {
  if (s3?.bucket && s3.key) {
    return `Resume tailored successfully. Saved to s3://${s3.bucket}/${s3.key}`;
  }
  return 'Resume tailored successfully.';
}

export async function tailorResume(job: JobListing): Promise<TailorResumeResponse> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(job.jobId)}/tailor-resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jobId: job.jobId,
      title: job.title,
      company: job.company,
      location: job.location,
      date: job.date,
      url: job.url,
      source: job.source,
      status: job.status,
      jobDescription: job.jobDescription,
      analysisStatus: job.analysisStatus,
      applied: job.applied,
      emailId: job.emailId,
      updatedAt: job.updatedAt ?? '',
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  const data = (await response.json()) as TailorResumeResponse;
  return data;
}
