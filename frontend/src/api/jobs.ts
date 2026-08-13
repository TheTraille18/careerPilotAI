import type { AnalysisStatus, FitStatus, JobListing, JobStatus, JobsResponse } from '../types/job';
import { apiFetch } from './http';

export type JobCreateInput = {
  title: string;
  company?: string;
  location?: string;
  url?: string;
  source?: string;
  jobDescription?: string;
};

export async function createJob(input: JobCreateInput): Promise<JobListing> {
  const response = await apiFetch('/api/jobs', {
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
  const response = await apiFetch('/api/jobs');
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
  const response = await apiFetch(`/api/jobs/${encodeURIComponent(jobId)}?${params}`);
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
  const response = await apiFetch(`/api/jobs/${encodeURIComponent(jobId)}/description`, {
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

/** Load full job description text for viewing (S3 / inline / demo JSON). */
export async function fetchJobDescriptionText(
  jobId: string,
  source: string,
): Promise<string> {
  const params = new URLSearchParams({ source });
  const response = await apiFetch(
    `/api/jobs/${encodeURIComponent(jobId)}/description?${params}`,
  );
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      const body = await response.text();
      if (body) message = body;
    }
    throw new Error(message);
  }
  const data = (await response.json()) as { text?: string };
  return (data.text || '').trim();
}

export async function fetchJobDescriptionFromUrl(
  jobId: string,
  source: string,
): Promise<{ job: JobListing; fetchedText: string }> {
  const response = await apiFetch(
    `/api/jobs/${encodeURIComponent(jobId)}/description/fetch`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source }),
    },
  );

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      const body = await response.text();
      if (body) message = body;
    }
    throw new Error(message);
  }

  return response.json() as Promise<{ job: JobListing; fetchedText: string }>;
}

export async function updateAnalysisStatus(
  jobId: string,
  source: string,
  analysisStatus: AnalysisStatus,
): Promise<JobListing> {
  const response = await apiFetch(`/api/jobs/${encodeURIComponent(jobId)}/analysis-status`, {
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

export async function updateJobStatus(
  jobId: string,
  source: string,
  status: JobStatus,
): Promise<JobListing> {
  const response = await apiFetch(`/api/jobs/${encodeURIComponent(jobId)}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, status }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  const data = (await response.json()) as { job: JobListing };
  return data.job;
}

export async function updateApplied(
  jobId: string,
  source: string,
  applied: 'Yes' | 'No',
): Promise<JobListing> {
  const response = await apiFetch(`/api/jobs/${encodeURIComponent(jobId)}/applied`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, applied }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  const data = (await response.json()) as { job: JobListing };
  return data.job;
}

export type FitCheckTodayResponse = {
  date: string;
  candidateCount: number;
  evaluated: number;
  withDescription?: number;
  skippedExisting: number;
  errorCount: number;
  results: Array<{
    jobId: string;
    source: string;
    title?: string;
    fit?: string;
    reason?: string;
    skipped?: boolean;
    descriptionSource?: string;
  }>;
  errors: Array<{
    jobId: string;
    source: string;
    title?: string;
    error: string;
  }>;
};

export async function checkTodaysFit(options?: {
  force?: boolean;
  limit?: number;
}): Promise<FitCheckTodayResponse> {
  const response = await apiFetch('/api/jobs/fit-check-today', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      force: options?.force ?? false,
      limit: options?.limit ?? 50,
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  return response.json() as Promise<FitCheckTodayResponse>;
}

export type FitCheckJobResponse = {
  job: JobListing;
  fit?: string;
  reason?: string;
  descriptionSource?: string;
};

export async function checkJobFit(
  jobId: string,
  source: string,
  jobDescription = '',
): Promise<FitCheckJobResponse> {
  const response = await apiFetch(`/api/jobs/${encodeURIComponent(jobId)}/fit-check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, jobDescription }),
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      const body = await response.text();
      if (body) message = body;
    }
    throw new Error(message);
  }

  return response.json() as Promise<FitCheckJobResponse>;
}

export async function updateFit(
  jobId: string,
  source: string,
  fit: FitStatus,
  reason = '',
): Promise<JobListing> {
  const response = await apiFetch(`/api/jobs/${encodeURIComponent(jobId)}/fit`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, fit, reason }),
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
  eval?: JobListing['evalResult'];
};

export function formatTailorSuccessMessage(s3?: TailorResumeResponse['s3']): string {
  if (s3?.bucket && s3.key) {
    return `Resume tailored successfully. Saved to s3://${s3.bucket}/${s3.key}`;
  }
  return 'Resume tailored successfully.';
}

export async function tailorResume(job: JobListing): Promise<TailorResumeResponse> {
  const response = await apiFetch(`/api/jobs/${encodeURIComponent(job.jobId)}/tailor-resume`, {
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
      appliedDate: job.appliedDate ?? '',
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

function filenameFromContentDisposition(header: string | null): string | null {
  if (!header) return null;
  const utfMatch = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (utfMatch?.[1]) {
    try {
      return decodeURIComponent(utfMatch[1].trim());
    } catch {
      return utfMatch[1].trim();
    }
  }
  const plainMatch = /filename="?([^";]+)"?/i.exec(header);
  return plainMatch?.[1]?.trim() || null;
}

/** Download the latest tailored resume .docx for a job from S3 via the API. */
export async function downloadTailoredResume(jobId: string): Promise<void> {
  const response = await apiFetch(`/api/jobs/${encodeURIComponent(jobId)}/tailored-resume`);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  const blob = await response.blob();
  const filename =
    filenameFromContentDisposition(response.headers.get('Content-Disposition')) ||
    'tailored_resume.docx';
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

export type CoverLetterResponse = {
  job: JobListing;
  s3?: {
    bucket: string;
    key: string;
    filename?: string;
  };
};

export function formatCoverLetterSuccessMessage(s3?: CoverLetterResponse['s3']): string {
  if (s3?.bucket && s3.key) {
    return `Cover letter generated. Saved to s3://${s3.bucket}/${s3.key}`;
  }
  return 'Cover letter generated successfully.';
}

export async function generateCoverLetter(job: JobListing): Promise<CoverLetterResponse> {
  const response = await apiFetch(`/api/jobs/${encodeURIComponent(job.jobId)}/cover-letter`, {
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
      appliedDate: job.appliedDate ?? '',
      emailId: job.emailId,
      updatedAt: job.updatedAt ?? '',
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  return (await response.json()) as CoverLetterResponse;
}

/** Download the latest cover letter .docx for a job from S3 via the API. */
export async function downloadCoverLetter(jobId: string): Promise<void> {
  const response = await apiFetch(`/api/jobs/${encodeURIComponent(jobId)}/cover-letter`);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  const blob = await response.blob();
  const filename =
    filenameFromContentDisposition(response.headers.get('Content-Disposition')) ||
    'cover_letter.docx';
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}
