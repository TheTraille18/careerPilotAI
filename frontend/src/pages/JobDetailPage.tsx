import { useCallback, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { fetchJob, formatTailorSuccessMessage, tailorResume } from '../api/jobs';
import type { AnalysisStatus, JobListing } from '../types/job';
import { ANALYSIS_STATUSES } from '../types/job';
import '../App.css';

const SOURCE_LABELS: Record<string, string> = {
  linkedin: 'LinkedIn',
  dice: 'Dice',
  indeed: 'Indeed',
  careerbuilder: 'CareerBuilder',
  manual: 'Manual',
};

function formatDate(value: string): string {
  if (!value) return 'n/a';
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value;
  return new Date(parsed).toLocaleString();
}

function normalizeAnalysisStatus(value: string | undefined): AnalysisStatus {
  const text = value?.trim() || '';
  if ((ANALYSIS_STATUSES as readonly string[]).includes(text)) {
    return text as AnalysisStatus;
  }
  return 'Pending';
}

function normalizeJob(job: JobListing): JobListing {
  return {
    ...job,
    status: job.status?.trim() || 'Active',
    jobDescription: job.jobDescription?.trim() || 'Not available',
    analysisStatus: normalizeAnalysisStatus(job.analysisStatus),
    applied: job.applied?.trim() || 'No',
  };
}

export default function JobDetailPage() {
  const { jobId = '' } = useParams<{ jobId: string }>();
  const [searchParams] = useSearchParams();
  const source = searchParams.get('source')?.trim() || '';

  const [job, setJob] = useState<JobListing | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tailorError, setTailorError] = useState<string | null>(null);
  const [tailorSuccess, setTailorSuccess] = useState<string | null>(null);
  const [tailoring, setTailoring] = useState(false);

  const loadJob = useCallback(async () => {
    if (!jobId || !source) {
      setJob(null);
      setError('Missing job id or source query parameter.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await fetchJob(jobId, source);
      setJob(normalizeJob(data));
    } catch (err) {
      setJob(null);
      setError(err instanceof Error ? err.message : 'Failed to load job');
    } finally {
      setLoading(false);
    }
  }, [jobId, source]);

  useEffect(() => {
    void loadJob();
  }, [loadJob]);

  const fields = job
    ? [
        { label: 'Job ID', value: job.jobId || 'n/a' },
        { label: 'Title', value: job.title || 'n/a' },
        { label: 'Company', value: job.company || 'n/a' },
        { label: 'Location', value: job.location || 'n/a' },
        { label: 'Source', value: SOURCE_LABELS[job.source] ?? job.source ?? 'n/a' },
        { label: 'Status', value: job.status },
        { label: 'Job Description', value: job.jobDescription },
        { label: 'Analysis Status', value: normalizeAnalysisStatus(job.analysisStatus) },
        { label: 'Applied', value: job.applied },
        { label: 'Date', value: formatDate(job.date) },
        { label: 'Email ID', value: job.emailId || 'n/a' },
        { label: 'Updated At', value: job.updatedAt ? formatDate(job.updatedAt) : 'n/a' },
      ]
    : [];

  return (
    <div className="app-shell">
      <header className="page-header">
        <div className="page-header-top">
          <div>
            <h1>Job details</h1>
            <p>Loaded from GET /api/jobs/{'{job_id}'}?source=...</p>
          </div>
          <div className="header-actions">
            <Link to="/" className="btn-secondary link-button">
              Back to jobs
            </Link>
            <button type="button" className="btn-primary" onClick={() => void loadJob()} disabled={loading}>
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>
      </header>

      <main className="page-main">
        {error && <div className="job-panel-error">{error}</div>}

        {loading && !job && <div className="job-panel-empty">Loading job...</div>}

        {!loading && job && (
          <section className="job-full-detail">
            <div className="job-full-detail-header">
              <h2>{job.title || 'Untitled'}</h2>
              <p>
                {job.company || 'n/a'}
                {job.location ? ` � ${job.location}` : ''}
              </p>
              {job.url ? (
                <p>
                  <a href={job.url} target="_blank" rel="noreferrer">
                    Open job posting
                  </a>
                </p>
              ) : null}
            </div>

            <dl className="job-detail-fields">
              {fields.map(({ label, value }) => (
                <div key={label} className="job-detail-row">
                  <dt>{label}</dt>
                  <dd title={value}>{value}</dd>
                </div>
              ))}
            </dl>

            {tailorError && <div className="job-panel-error">{tailorError}</div>}
            {tailorSuccess && <div className="job-panel-success">{tailorSuccess}</div>}

            <div className="job-full-detail-actions">
              <button
                type="button"
                className="btn-primary"
                disabled={tailoring}
                onClick={() => {
                  void (async () => {
                    if (job.jobDescription?.trim() !== 'Available') {
                      setTailorError(
                        'Job description is not available. Paste and save a description first.',
                      );
                      setTailorSuccess(null);
                      return;
                    }

                    setTailoring(true);
                    setTailorError(null);
                    setTailorSuccess(null);
                    try {
                      const result = await tailorResume(job);
                      setJob(normalizeJob(result.job));
                      setTailorSuccess(formatTailorSuccessMessage(result.s3));
                    } catch (err) {
                      setTailorError(
                        err instanceof Error ? err.message : 'Failed to tailor resume',
                      );
                      setTailorSuccess(null);
                    } finally {
                      setTailoring(false);
                    }
                  })();
                }}
              >
                {tailoring ? 'Tailoring...' : 'Tailor Resume'}
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
