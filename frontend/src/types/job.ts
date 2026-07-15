export type JobSource = 'linkedin' | 'dice' | 'indeed' | 'careerbuilder' | 'manual' | string;

export const ANALYSIS_STATUSES = [
  'Pending',
  'In_Progress',
  'Completed',
  'Failed',
  'Retry',
] as const;

export type AnalysisStatus = (typeof ANALYSIS_STATUSES)[number];

export interface JobListing {
  jobId: string;
  title: string;
  company: string;
  location: string;
  date: string;
  url: string;
  source: JobSource;
  status: string;
  jobDescription: string;
  analysisStatus: AnalysisStatus | string;
  applied: string;
  emailId: string;
  updatedAt?: string;
}

export interface JobsResponse {
  jobs: JobListing[];
  count: number;
  table?: string;
  analysisStatuses?: readonly string[];
}
