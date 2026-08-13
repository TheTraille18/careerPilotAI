export type JobSource =
  | 'linkedin'
  | 'dice'
  | 'indeed'
  | 'careerbuilder'
  | 'remoterocketship'
  | 'aiapply'
  | 'manual'
  | string;

export const ANALYSIS_STATUSES = [
  'Pending',
  'Tailored Resume',
  'Cover Letter',
] as const;

export type AnalysisStatus = (typeof ANALYSIS_STATUSES)[number];

export const JOB_STATUSES = [
  'Active',
  'Applied',
  'Interview',
  'Offer',
  'Rejected',
  'Closed',
  'Not Enough Experience',
] as const;

export type JobStatus = (typeof JOB_STATUSES)[number];

export const FIT_STATUSES = ['Unset', 'Apply', 'Maybe', 'Skip'] as const;

export type FitStatus = (typeof FIT_STATUSES)[number];

export interface EvalViolation {
  paragraphId?: string;
  type?: string;
  quote?: string;
  explanation?: string;
}

export interface EvalScores {
  grounding?: number;
  ruleCompliance?: number;
  jobFit?: number;
  minimalChange?: number;
  readability?: number;
}

export interface EvalChange {
  paragraphId?: string;
  operation?: 'replace' | 'delete' | string;
  originalText?: string;
  newText?: string;
  reason?: string;
  evidence?: string;
}

export interface EvalResult {
  pass?: boolean;
  overallScore?: number;
  scores?: EvalScores;
  hardFails?: string[];
  violations?: EvalViolation[];
  changes?: EvalChange[];
  changedParagraphCount?: number;
  summary?: string;
  evaluatedAt?: string;
}

export interface JobListing {
  jobId: string;
  title: string;
  company: string;
  location: string;
  date: string;
  url: string;
  source: JobSource;
  status: JobStatus | string;
  jobDescription: string;
  analysisStatus: AnalysisStatus | string;
  applied: string;
  appliedDate?: string;
  emailId: string;
  updatedAt?: string;
  evalResult?: EvalResult | null;
  fit?: FitStatus | string;
  fitReason?: string;
  fitCheckedAt?: string;
}

export interface JobsResponse {
  jobs: JobListing[];
  count: number;
  table?: string;
  analysisStatuses?: readonly string[];
  jobStatuses?: readonly string[];
  fitStatuses?: readonly string[];
}
