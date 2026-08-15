import { useCallback, useEffect, useMemo, useState } from 'react';
import { Route, Routes, useNavigate, useSearchParams } from 'react-router-dom';
import { fetchJobs, createJob, updateJobStatus, updateJobDescription, fetchJobDescriptionFromUrl, checkTodaysFit, checkJobFit } from './api/jobs';
import type { AnalysisStatus, FitStatus, JobListing, JobStatus } from './types/job';
import { ANALYSIS_STATUSES, FIT_STATUSES, JOB_STATUSES } from './types/job';
import JobDetailPage from './pages/JobDetailPage';
import { AdminProvider, useAdmin } from './auth/AdminContext';
import ProfileButton from './components/ProfileButton';
import DemoModeBanner from './components/DemoModeBanner';
import Tip from './components/Tip';
import './App.css';

const INACTIVE_STATUSES = new Set(['Closed', 'Rejected', 'Not Enough Experience']);

const SOURCE_LABELS: Record<string, string> = {
  linkedin: 'LinkedIn',
  dice: 'Dice',
  indeed: 'Indeed',
  careerbuilder: 'CareerBuilder',
  remoterocketship: 'Remote Rocketship',
  aiapply: 'AIApply',
  manual: 'Manual',
};

const JOB_SOURCE_OPTIONS = [
  'manual',
  'linkedin',
  'dice',
  'indeed',
  'careerbuilder',
  'remoterocketship',
  'aiapply',
] as const;

type ColumnKey =
  | 'jobId'
  | 'title'
  | 'jobDescription'
  | 'company'
  | 'location'
  | 'source'
  | 'status'
  | 'fit'
  | 'analysisStatus'
  | 'applied'
  | 'date';

const COLUMN_FILTERS: { key: ColumnKey; label: string }[] = [
  { key: 'jobId', label: 'Job ID' },
  { key: 'title', label: 'Title' },
  { key: 'jobDescription', label: 'Job Description' },
  { key: 'company', label: 'Company' },
  { key: 'location', label: 'Location' },
  { key: 'source', label: 'Source' },
  { key: 'status', label: 'Status' },
  { key: 'fit', label: 'Fit' },
  { key: 'analysisStatus', label: 'Analysis Status' },
  { key: 'applied', label: 'Applied Date' },
  { key: 'date', label: 'Date' },
];

const EMPTY_FILTERS: Record<ColumnKey, string> = {
  jobId: '',
  title: '',
  jobDescription: '',
  company: '',
  location: '',
  source: '',
  status: '',
  fit: '',
  analysisStatus: '',
  applied: '',
  date: '',
};

type JobsTab = 'active' | 'applied' | 'interview' | 'inactive';

function parseJobsTab(value: string | null): JobsTab {
  if (value === 'applied' || value === 'interview' || value === 'inactive' || value === 'active') {
    return value;
  }
  return 'active';
}

function filtersFromSearchParams(searchParams: URLSearchParams): Record<ColumnKey, string> {
  const next = { ...EMPTY_FILTERS };
  for (const { key } of COLUMN_FILTERS) {
    next[key] = searchParams.get(key) || '';
  }
  return next;
}

function listStateToSearchParams(
  filters: Record<ColumnKey, string>,
  globalSearch: string,
  activeTab: JobsTab,
): URLSearchParams {
  const next = new URLSearchParams();
  if (activeTab !== 'active') next.set('tab', activeTab);
  const q = globalSearch.trim();
  if (q) next.set('q', q);
  for (const { key } of COLUMN_FILTERS) {
    const value = filters[key].trim();
    if (value) next.set(key, value);
  }
  return next;
}

function formatDate(value: string): string {
  if (!value) return 'n/a';
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value;
  return new Date(parsed).toLocaleString();
}

/** Format AppliedDate (YYYY-MM-DD or ISO) for table/detail display. */
function formatAppliedDate(value: string | undefined): string {
  const text = value?.trim() || '';
  if (!text) return '';
  // Date-only values parse as UTC midnight; format as local calendar date.
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    const [year, month, day] = text.split('-').map(Number);
    return new Date(year, month - 1, day).toLocaleDateString();
  }
  const parsed = Date.parse(text);
  if (Number.isNaN(parsed)) return text;
  return new Date(parsed).toLocaleDateString();
}

function getColumnValue(job: JobListing, key: ColumnKey): string {
  switch (key) {
    case 'jobId':
      return job.jobId || 'n/a';
    case 'title':
      return job.title || 'n/a';
    case 'jobDescription':
      return job.jobDescription?.trim() || 'Not available';
    case 'company':
      return job.company || 'n/a';
    case 'location':
      return job.location || 'n/a';
    case 'source':
      return SOURCE_LABELS[job.source] ?? job.source ?? 'n/a';
    case 'status':
      return normalizeJobStatus(job.status);
    case 'fit':
      return normalizeFitStatus(job.fit);
    case 'analysisStatus':
      return normalizeAnalysisStatus(job.analysisStatus);
    case 'applied':
      return formatAppliedDate(job.appliedDate) || job.applied?.trim() || 'No';
    case 'date':
      return formatDate(job.date);
  }
}

function normalizeAnalysisStatus(value: string | undefined): AnalysisStatus {
  const text = value?.trim() || '';
  if ((ANALYSIS_STATUSES as readonly string[]).includes(text)) {
    return text as AnalysisStatus;
  }
  return 'Pending';
}

function normalizeJobStatus(value: string | undefined): JobStatus {
  const text = value?.trim() || '';
  if ((JOB_STATUSES as readonly string[]).includes(text)) {
    return text as JobStatus;
  }
  const matched = JOB_STATUSES.find((status) => status.toLowerCase() === text.toLowerCase());
  return matched ?? 'Active';
}

function normalizeFitStatus(value: string | undefined): FitStatus {
  const text = value?.trim() || '';
  if ((FIT_STATUSES as readonly string[]).includes(text)) {
    return text as FitStatus;
  }
  const matched = FIT_STATUSES.find((status) => status.toLowerCase() === text.toLowerCase());
  return matched ?? 'Unset';
}

function CopyIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="9" y="9" width="11" height="11" rx="2" stroke="currentColor" strokeWidth="2" />
      <path
        d="M5 15V5a2 2 0 0 1 2-2h10"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M5 12l5 5L20 7"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function JobIdCell({ jobId }: { jobId: string }) {
  const [copied, setCopied] = useState(false);

  const copyJobId = async () => {
    try {
      await navigator.clipboard.writeText(jobId);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <td className="job-id-cell" onClick={(event) => event.stopPropagation()}>
      <div className="job-id-row">
        <Tip text="Copy this job ID to the clipboard">
          <button
            type="button"
            className={`copy-job-id${copied ? ' copied' : ''}`}
            onClick={() => void copyJobId()}
            aria-label={copied ? 'Job ID copied' : 'Copy Job ID'}
          >
            {copied ? <CheckIcon /> : <CopyIcon />}
          </button>
        </Tip>
        <span className="job-id-text" title={jobId}>
          {jobId}
        </span>
      </div>
    </td>
  );
}

function JobDescriptionCell({
  value,
  onOpen,
}: {
  value: string;
  onOpen: () => void;
}) {
  const { canEdit } = useAdmin();
  return (
    <td className="job-description-cell" onClick={(event) => event.stopPropagation()}>
      <Tip
        text={
          canEdit
            ? 'Open the job description editor to paste, fetch, or update the JD'
            : 'Admin sign-in required to edit job descriptions'
        }
      >
        <button
          type="button"
          className="job-description-trigger"
          onClick={onOpen}
          disabled={!canEdit}
        >
          {value}
        </button>
      </Tip>
    </td>
  );
}

function AnalysisStatusCell({ job }: { job: JobListing }) {
  return (
    <td className="analysis-status-cell">{normalizeAnalysisStatus(job.analysisStatus)}</td>
  );
}

function FitCell({ job }: { job: JobListing }) {
  const fit = normalizeFitStatus(job.fit);
  const reason = job.fitReason?.trim() || '';
  const tip =
    reason ||
    (fit === 'Unset'
      ? 'Fit not scored yet — use Check fit after a job description is available'
      : `Fit verdict: ${fit}`);
  return (
    <td className="fit-cell" onClick={(event) => event.stopPropagation()}>
      <Tip text={tip}>
        <span className={`fit-badge fit-${fit.toLowerCase()}`}>{fit}</span>
      </Tip>
    </td>
  );
}

function JobStatusCell({
  job,
  onUpdated,
}: {
  job: JobListing;
  onUpdated: (job: JobListing) => void;
}) {
  const { canEdit } = useAdmin();
  const [saving, setSaving] = useState(false);
  const value = normalizeJobStatus(job.status);

  const onChange = async (next: JobStatus) => {
    if (next === value) return;
    setSaving(true);
    try {
      const updated = await updateJobStatus(job.jobId, job.source, next);
      onUpdated(normalizeJob(updated));
    } catch {
      // Keep previous value in the select via controlled value from job state.
    } finally {
      setSaving(false);
    }
  };

  return (
    <td className="job-status-cell" onClick={(event) => event.stopPropagation()}>
      <Tip
        text={
          canEdit
            ? 'Change this job’s pipeline status (Active, Applied, Interview, etc.)'
            : 'Admin sign-in required to change job status'
        }
      >
        <select
          className="job-status-select"
          aria-label="Status"
          value={value}
          disabled={saving || !canEdit}
          onChange={(event) => void onChange(event.target.value as JobStatus)}
        >
          {JOB_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </Tip>
    </td>
  );
}

function AddJobModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (job: JobListing) => void;
}) {
  const [title, setTitle] = useState('');
  const [company, setCompany] = useState('');
  const [location, setLocation] = useState('');
  const [url, setUrl] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [source, setSource] = useState<(typeof JOB_SOURCE_OPTIONS)[number]>('manual');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !saving) onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, saving]);

  const save = async () => {
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setError('Title is required.');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const created = await createJob({
        title: trimmedTitle,
        company: company.trim(),
        location: location.trim(),
        url: url.trim(),
        source,
        jobDescription: jobDescription.trim(),
      });
      onCreated(normalizeJob(created));
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add job');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !saving) onClose();
      }}
    >
      <div
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-job-modal-title"
      >
        <div className="modal-header">
          <div>
            <h2 id="add-job-modal-title">Add Job</h2>
            <p>Enter job details to add a new listing.</p>
          </div>
          <Tip text="Close without adding a job">
            <button
              type="button"
              className="btn-secondary modal-close"
              onClick={onClose}
              disabled={saving}
              aria-label="Close"
            >
              Close
            </button>
          </Tip>
        </div>

        <div className="job-form-fields">
          <label className="job-form-field">
            <span>Title *</span>
            <input
              type="text"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Software Engineer"
              autoFocus
            />
          </label>
          <label className="job-form-field">
            <span>Company</span>
            <input
              type="text"
              value={company}
              onChange={(event) => setCompany(event.target.value)}
              placeholder="Acme Corp"
            />
          </label>
          <label className="job-form-field">
            <span>Location</span>
            <input
              type="text"
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              placeholder="Remote"
            />
          </label>
          <label className="job-form-field">
            <span>Job URL</span>
            <input
              type="url"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://..."
            />
          </label>
          <label className="job-form-field">
            <span>Source</span>
            <select value={source} onChange={(event) => setSource(event.target.value as typeof source)}>
              {JOB_SOURCE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {SOURCE_LABELS[option] ?? option}
                </option>
              ))}
            </select>
          </label>
          <label className="job-form-field">
            <span>Job Description</span>
            <textarea
              className="job-description-textarea"
              value={jobDescription}
              onChange={(event) => setJobDescription(event.target.value)}
              placeholder="Paste the job description here..."
              spellCheck
            />
          </label>
        </div>

        {error && <div className="job-panel-error">{error}</div>}

        <div className="modal-actions">
          <Tip text="Close without adding a job">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={saving}>
              Cancel
            </button>
          </Tip>
          <Tip text="Create this job listing in CareerPilot">
            <button type="button" className="btn-primary" onClick={() => void save()} disabled={saving}>
              {saving ? 'Adding...' : 'Add Job'}
            </button>
          </Tip>
        </div>
      </div>
    </div>
  );
}

function JobDetailModal({
  job,
  onClose,
  onEditDescription,
  onUpdated,
}: {
  job: JobListing;
  onClose: () => void;
  onEditDescription: () => void;
  onUpdated: (job: JobListing) => void;
}) {
  const navigate = useNavigate();
  const [listSearchParams] = useSearchParams();
  const { canEdit } = useAdmin();
  const [checkingFit, setCheckingFit] = useState(false);
  const [fitError, setFitError] = useState<string | null>(null);
  const [fitSuccess, setFitSuccess] = useState<string | null>(null);

  const desc = job.jobDescription?.trim() || 'Not available';
  const hasDescription =
    desc === 'Available' || (desc !== 'Not available' && desc.length >= 40);
  const busy = checkingFit;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, busy]);

  const fields: { label: string; value: string }[] = [
    { label: 'Job ID', value: job.jobId || 'n/a' },
    { label: 'Title', value: job.title || 'n/a' },
    { label: 'Company', value: job.company || 'n/a' },
    { label: 'Location', value: job.location || 'n/a' },
    { label: 'Source', value: SOURCE_LABELS[job.source] ?? job.source ?? 'n/a' },
    { label: 'Status', value: job.status?.trim() || 'Active' },
    { label: 'Fit', value: normalizeFitStatus(job.fit) },
    { label: 'Fit reason', value: job.fitReason?.trim() || 'n/a' },
    { label: 'Job Description', value: job.jobDescription?.trim() || 'Not available' },
    { label: 'Analysis Status', value: normalizeAnalysisStatus(job.analysisStatus) },
    { label: 'Applied', value: formatAppliedDate(job.appliedDate) || job.applied?.trim() || 'No' },
    { label: 'Date', value: formatDate(job.date) },
  ];

  const openFullDetails = () => {
    const params = new URLSearchParams({ source: job.source });
    const listQuery = listSearchParams.toString();
    if (listQuery) params.set('return', listQuery);
    navigate(`/jobs/${encodeURIComponent(job.jobId)}?${params}`);
  };

  const onCheckFit = async () => {
    if (!hasDescription) {
      setFitError('Paste and save a job description before checking fit');
      setFitSuccess(null);
      return;
    }

    setCheckingFit(true);
    setFitError(null);
    setFitSuccess(null);
    try {
      // Empty paste → backend uses Available/S3 or inline stored text.
      const pasted = desc === 'Available' || desc === 'Not available' ? '' : desc;
      const result = await checkJobFit(job.jobId, job.source, pasted);
      const updated = normalizeJob(result.job);
      onUpdated(updated);
      setFitSuccess(`${updated.fit}: ${updated.fitReason || 'No reason provided.'}`);
    } catch (err) {
      setFitError(err instanceof Error ? err.message : 'Fit check failed');
      setFitSuccess(null);
    } finally {
      setCheckingFit(false);
    }
  };

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !busy) onClose();
      }}
    >
      <div
        className="modal-panel job-detail-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="job-detail-modal-title"
      >
        <div className="modal-header">
          <div>
            <h2 id="job-detail-modal-title">Job Details</h2>
            <p>
              {job.title || 'Untitled'}
              {job.company ? ` · ${job.company}` : ''}
            </p>
          </div>
          <Tip text="Close this dialog">
            <button
              type="button"
              className="btn-secondary modal-close"
              onClick={onClose}
              disabled={busy}
              aria-label="Close"
            >
              Close
            </button>
          </Tip>
        </div>

        <dl className="job-detail-fields">
          {fields.map(({ label, value }) => (
            <div key={label} className="job-detail-row">
              <dt>{label}</dt>
              <dd title={value}>{value}</dd>
            </div>
          ))}
          <div className="job-detail-row">
            <dt>Source URL</dt>
            <dd>
              {job.url ? (
                <Tip text="Open the original job posting in a new tab">
                  <a href={job.url} target="_blank" rel="noreferrer">
                    Open job posting
                  </a>
                </Tip>
              ) : (
                'n/a'
              )}
            </dd>
          </div>
        </dl>

        {fitError && <div className="job-panel-error">{fitError}</div>}
        {fitSuccess && <div className="job-panel-success">{fitSuccess}</div>}

        <div className="modal-actions">
          <Tip
            text={
              canEdit
                ? 'Open the editor to paste, fetch, or update this job description'
                : 'Admin sign-in required to edit descriptions'
            }
          >
            <button type="button" className="btn-secondary" onClick={onEditDescription} disabled={busy || !canEdit}>
              Edit description
            </button>
          </Tip>
          <Tip
            text={
              !canEdit
                ? 'Admin sign-in required for AI fit checks'
                : hasDescription
                  ? 'Run AI fit scoring using the saved or pasted job description'
                  : 'Add a job description before checking fit'
            }
          >
            <button
              type="button"
              className="btn-secondary"
              onClick={() => void onCheckFit()}
              disabled={busy || !hasDescription || !canEdit}
            >
              {checkingFit ? 'Checking fit...' : 'Check fit'}
            </button>
          </Tip>
          <Tip text="Open the full job details page with eval results and resume tools">
            <button type="button" className="btn-primary" onClick={openFullDetails} disabled={busy}>
              Full details
            </button>
          </Tip>
        </div>
      </div>
    </div>
  );
}

function JobDescriptionModal({
  job,
  onClose,
  onSaved,
}: {
  job: JobListing;
  onClose: () => void;
  onSaved: (job: JobListing) => void;
}) {
  const { canEdit } = useAdmin();
  const initial =
    job.jobDescription?.trim() === 'Not available' ||
    job.jobDescription?.trim() === 'Available'
      ? ''
      : (job.jobDescription ?? '');
  const [text, setText] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [checkingFit, setCheckingFit] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fitMessage, setFitMessage] = useState<string | null>(null);
  const [currentFit, setCurrentFit] = useState(normalizeFitStatus(job.fit));
  const [currentFitReason, setCurrentFitReason] = useState(job.fitReason?.trim() || '');

  const hasStoredDescription = job.jobDescription?.trim() === 'Available';
  const hasPastedText = text.trim().length >= 40;
  const canCheckFit = hasPastedText || hasStoredDescription;
  const busy = saving || fetching || checkingFit;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, busy]);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateJobDescription(job.jobId, job.source, text);
      onSaved(normalizeJob(updated));
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save description');
    } finally {
      setSaving(false);
    }
  };

  const fetchFromUrl = async () => {
    if (!job.url?.trim()) {
      setError('This job has no URL to fetch');
      return;
    }
    setFetching(true);
    setError(null);
    try {
      const result = await fetchJobDescriptionFromUrl(job.jobId, job.source);
      setText(result.fetchedText);
      onSaved(normalizeJob(result.job));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to fetch description from URL — paste it instead',
      );
    } finally {
      setFetching(false);
    }
  };

  const runFitCheck = async () => {
    if (!canCheckFit) {
      setError('Paste a job description (or save/fetch one) before checking fit');
      return;
    }
    setCheckingFit(true);
    setError(null);
    setFitMessage(null);
    try {
      const result = await checkJobFit(job.jobId, job.source, text.trim());
      const updated = normalizeJob(result.job);
      onSaved(updated);
      setCurrentFit(normalizeFitStatus(updated.fit));
      setCurrentFitReason(updated.fitReason?.trim() || '');
      setFitMessage(`${updated.fit}: ${updated.fitReason || 'No reason provided.'}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fit check failed');
    } finally {
      setCheckingFit(false);
    }
  };

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !busy) onClose();
      }}
    >
      <div
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="job-description-modal-title"
      >
        <div className="modal-header">
          <div>
            <h2 id="job-description-modal-title">Job Description</h2>
            <p>
              {job.title || 'Untitled'}
              {job.company ? ` · ${job.company}` : ''}
            </p>
            <p className="modal-job-id" title={job.jobId}>
              Job ID: {job.jobId}
            </p>
            {job.url ? (
              <p className="modal-job-link">
                <Tip text="Open the original job posting in a new tab">
                  <a href={job.url} target="_blank" rel="noreferrer">
                    Open job posting
                  </a>
                </Tip>
              </p>
            ) : (
              <p className="modal-job-link muted">No job URL available</p>
            )}
            {currentFit !== 'Unset' && (
              <p className="modal-fit-line">
                Fit:{' '}
                <Tip text={currentFitReason || `Fit verdict: ${currentFit}`}>
                  <span className={`fit-badge fit-${currentFit.toLowerCase()}`}>{currentFit}</span>
                </Tip>
                {currentFitReason ? ` — ${currentFitReason}` : ''}
              </p>
            )}
          </div>
          <Tip text="Close without saving">
            <button
              type="button"
              className="btn-secondary modal-close"
              onClick={onClose}
              disabled={busy}
              aria-label="Close"
            >
              Close
            </button>
          </Tip>
        </div>

        <textarea
          className="job-description-textarea"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={
            hasStoredDescription
              ? 'Description already saved — paste to replace, or Check fit using the saved JD...'
              : 'Paste the job description here, or fetch from the public job URL...'
          }
          autoFocus
          spellCheck
          disabled={busy}
        />

        {error && <div className="job-panel-error">{error}</div>}
        {fitMessage && <div className="job-panel-success">{fitMessage}</div>}

        <div className="modal-actions">
          <Tip
            text={
              !canEdit
                ? 'Admin sign-in required'
                : job.url
                  ? 'Try fetching the public job posting text from the job URL'
                  : 'This listing has no URL to fetch from'
            }
          >
            <button
              type="button"
              className="btn-secondary"
              onClick={() => void fetchFromUrl()}
              disabled={busy || !job.url?.trim() || !canEdit}
            >
              {fetching ? 'Fetching...' : 'Fetch from URL'}
            </button>
          </Tip>
          <Tip
            text={
              !canEdit
                ? 'Admin sign-in required for AI fit checks'
                : canCheckFit
                  ? 'Run AI fit scoring using the pasted or saved description'
                  : 'Paste or save a job description before checking fit'
            }
          >
            <button
              type="button"
              className="btn-secondary"
              onClick={() => void runFitCheck()}
              disabled={busy || !canCheckFit || !canEdit}
            >
              {checkingFit ? 'Checking fit...' : 'Check fit'}
            </button>
          </Tip>
          <Tip text="Close without saving">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>
              Cancel
            </button>
          </Tip>
          <Tip
            text={
              canEdit
                ? 'Save this job description text to CareerPilot storage'
                : 'Admin sign-in required to save descriptions'
            }
          >
            <button
              type="button"
              className="btn-primary"
              onClick={() => void save()}
              disabled={busy || !canEdit}
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </Tip>
        </div>
      </div>
    </div>
  );
}

function normalizeJob(job: JobListing): JobListing {
  return {
    ...job,
    status: normalizeJobStatus(job.status),
    jobDescription: job.jobDescription?.trim() || 'Not available',
    analysisStatus: normalizeAnalysisStatus(job.analysisStatus),
    applied: job.applied?.trim() || 'No',
    appliedDate: job.appliedDate?.trim() || '',
    fit: normalizeFitStatus(job.fit),
    fitReason: job.fitReason?.trim() || '',
    fitCheckedAt: job.fitCheckedAt?.trim() || '',
  };
}

function JobsPage() {
  const { authEnabled, isAdmin, email, canEdit } = useAdmin();
  const [searchParams, setSearchParams] = useSearchParams();
  const [jobs, setJobs] = useState<JobListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<ColumnKey, string>>(() =>
    filtersFromSearchParams(searchParams),
  );
  const [globalSearch, setGlobalSearch] = useState(() => searchParams.get('q') || '');
  const [activeTab, setActiveTab] = useState<JobsTab>(() => parseJobsTab(searchParams.get('tab')));
  const [editingJob, setEditingJob] = useState<JobListing | null>(null);
  const [selectedJob, setSelectedJob] = useState<JobListing | null>(null);
  const [addingJob, setAddingJob] = useState(false);
  const [checkingFit, setCheckingFit] = useState(false);
  const [fitMessage, setFitMessage] = useState<string | null>(null);

  useEffect(() => {
    const next = listStateToSearchParams(filters, globalSearch, activeTab);
    if (next.toString() === searchParams.toString()) return;
    setSearchParams(next, { replace: true });
  }, [filters, globalSearch, activeTab, searchParams, setSearchParams]);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJobs();
      setJobs(data.jobs.map(normalizeJob));
    } catch (err) {
      setJobs([]);
      setError(err instanceof Error ? err.message : 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  const columnOptions = useMemo(() => {
    const options: Record<ColumnKey, string[]> = {
      jobId: [],
      title: [],
      jobDescription: [],
      company: [],
      location: [],
      source: [],
      status: [],
      fit: [],
      analysisStatus: [],
      applied: [],
      date: [],
    };

    for (const column of COLUMN_FILTERS) {
      if (column.key === 'analysisStatus') {
        options.analysisStatus = [...ANALYSIS_STATUSES];
        continue;
      }
      if (column.key === 'status') {
        options.status = [...JOB_STATUSES];
        continue;
      }
      if (column.key === 'fit') {
        options.fit = [...FIT_STATUSES];
        continue;
      }
      const values = new Set<string>();
      for (const job of jobs) {
        values.add(getColumnValue(job, column.key));
      }
      options[column.key] = Array.from(values).sort((a, b) => a.localeCompare(b));
    }

    return options;
  }, [jobs]);

  const tabOf = useCallback((job: JobListing): JobsTab => {
    const status = normalizeJobStatus(job.status);
    if (INACTIVE_STATUSES.has(status)) return 'inactive';
    if (status === 'Interview') return 'interview';
    if (status === 'Applied') return 'applied';
    return 'active';
  }, []);

  const tabJobs = useMemo(
    () => jobs.filter((job) => tabOf(job) === activeTab),
    [jobs, activeTab, tabOf],
  );

  const tabCounts = useMemo(() => {
    const counts = { active: 0, applied: 0, interview: 0, inactive: 0 };
    for (const job of jobs) counts[tabOf(job)] += 1;
    return counts;
  }, [jobs, tabOf]);

  const filteredJobs = useMemo(() => {
    const globalQuery = globalSearch.trim().toLowerCase();

    return tabJobs.filter((job) => {
      const matchesColumns = COLUMN_FILTERS.every(({ key }) => {
        const query = filters[key].trim().toLowerCase();
        if (!query) return true;
        return getColumnValue(job, key).toLowerCase().includes(query);
      });
      if (!matchesColumns) return false;

      if (!globalQuery) return true;
      return COLUMN_FILTERS.some(({ key }) =>
        getColumnValue(job, key).toLowerCase().includes(globalQuery),
      );
    });
  }, [tabJobs, filters, globalSearch]);

  const updateFilter = (key: ColumnKey, value: string) => {
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const clearFilters = () => {
    setFilters(EMPTY_FILTERS);
    setGlobalSearch('');
  };

  const hasActiveFilters =
    Object.values(filters).some((value) => value !== '') || globalSearch.trim() !== '';

  const handleJobCreated = (created: JobListing) => {
    setJobs((current) => [created, ...current.filter(
      (job) => !(job.jobId === created.jobId && job.source === created.source),
    )]);
  };

  const handleJobUpdated = (updated: JobListing) => {
    setJobs((current) =>
      current.map((job) =>
        job.jobId === updated.jobId && job.source === updated.source ? updated : job,
      ),
    );
    setSelectedJob((current) =>
      current && current.jobId === updated.jobId && current.source === updated.source
        ? updated
        : current,
    );
  };

  const handleCheckTodaysFit = async () => {
    setCheckingFit(true);
    setFitMessage(null);
    setError(null);
    try {
      const result = await checkTodaysFit({ force: true, limit: 50 });
      await loadJobs();
      const errorNote =
        result.errorCount > 0 ? ` · ${result.errorCount} error(s)` : '';
      setFitMessage(
        `Today (${result.date}): evaluated ${result.evaluated}` +
          ` (${result.withDescription ?? 0} with JD), skipped ${result.skippedExisting}` +
          `, of ${result.candidateCount}${errorNote}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fit check failed');
    } finally {
      setCheckingFit(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="page-header">
        <div className="page-header-top">
          <div>
            <h1>
              CareerPilot AI
              {authEnabled && !isAdmin ? <span className="demo-title-badge">Demo</span> : null}
            </h1>
            <p>
              {authEnabled && !isAdmin
                ? 'Sample showcase data'
                : 'Jobs from DynamoDB'}
              {!loading && ` · showing ${filteredJobs.length} of ${tabJobs.length}`}
              {authEnabled && isAdmin && email && ` · Admin (${email})`}
            </p>
          </div>
          <div className="header-actions">
            <Tip text="Search across all visible job columns">
              <input
                type="search"
                className="global-search-input"
                aria-label="Search all columns"
                placeholder="Search all columns..."
                value={globalSearch}
                onChange={(e) => setGlobalSearch(e.target.value)}
              />
            </Tip>
            <Tip text={canEdit ? 'Add a new job listing manually' : 'Admin sign-in required to add jobs'}>
              <button
                type="button"
                className="btn-add-job"
                onClick={() => setAddingJob(true)}
                aria-label="Add job"
                disabled={!canEdit}
              >
                +
              </button>
            </Tip>
            {hasActiveFilters && (
              <Tip text="Clear all column filters and the global search">
                <button type="button" className="btn-secondary" onClick={clearFilters}>
                  Clear filters
                </button>
              </Tip>
            )}
            <Tip
              text={
                canEdit
                  ? "Score today's jobs with AI (fetches public JDs when possible)"
                  : 'Admin sign-in required for AI fit checks'
              }
            >
              <button
                type="button"
                className="btn-secondary"
                onClick={() => void handleCheckTodaysFit()}
                disabled={loading || checkingFit || !canEdit}
              >
                {checkingFit ? 'Checking fit...' : "Check today's fit"}
              </button>
            </Tip>
            <Tip text="Reload the job list from the server">
              <button
                type="button"
                className="icon-action-button"
                onClick={() => void loadJobs()}
                disabled={loading}
                aria-label={loading ? 'Refreshing jobs' : 'Refresh jobs'}
              >
                <svg
                  className={`refresh-icon-svg${loading ? ' is-spinning' : ''}`}
                  viewBox="0 0 24 24"
                  width="20"
                  height="20"
                  aria-hidden="true"
                  focusable="false"
                >
                  <path
                    d="M20 12a8 8 0 1 1-2.2-5.4"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M20 4v5h-5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </Tip>
            <ProfileButton />
          </div>
        </div>
        {fitMessage && <div className="fit-check-message">{fitMessage}</div>}
        <DemoModeBanner />
      </header>

      <main className="page-main">
        <div className="job-tabs" role="tablist" aria-label="Job status tabs">
          <Tip text="Show Active jobs that are still in play" place="bottom">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'active'}
              className={`job-tab${activeTab === 'active' ? ' active' : ''}`}
              onClick={() => setActiveTab('active')}
            >
              Active ({tabCounts.active})
            </button>
          </Tip>
          <Tip text="Show jobs marked Applied" place="bottom">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'applied'}
              className={`job-tab${activeTab === 'applied' ? ' active' : ''}`}
              onClick={() => setActiveTab('applied')}
            >
              Applied ({tabCounts.applied})
            </button>
          </Tip>
          <Tip text="Show jobs currently in Interview" place="bottom">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'interview'}
              className={`job-tab${activeTab === 'interview' ? ' active' : ''}`}
              onClick={() => setActiveTab('interview')}
            >
              Interview ({tabCounts.interview})
            </button>
          </Tip>
          <Tip text="Show Closed, Rejected, and Not Enough Experience jobs" place="bottom">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'inactive'}
              className={`job-tab${activeTab === 'inactive' ? ' active' : ''}`}
              onClick={() => setActiveTab('inactive')}
            >
              Inactive ({tabCounts.inactive})
            </button>
          </Tip>
        </div>

        {error && <div className="job-panel-error">{error}</div>}

        {!loading && !error && jobs.length === 0 && (
          <div className="job-panel-empty">No jobs in DynamoDB yet. Run python gmail.py to import alerts.</div>
        )}

        {!loading && !error && jobs.length > 0 && tabJobs.length === 0 && (
          <div className="job-panel-empty">No {activeTab} jobs.</div>
        )}

        {!loading && !error && tabJobs.length > 0 && filteredJobs.length === 0 && (
          <div className="job-panel-empty">No jobs match the current search filters.</div>
        )}

        {(tabJobs.length > 0 || loading) && (
          <div className="table-wrap">
            <table className="jobs-table">
              <thead>
                <tr>
                  {COLUMN_FILTERS.map(({ label }) => (
                    <th key={label}>{label}</th>
                  ))}
                  <th>Link</th>
                </tr>
                <tr className="filter-row">
                  {COLUMN_FILTERS.map(({ key, label }) => {
                    const listId = `filter-options-${key}`;
                    return (
                      <th key={key}>
                        <Tip text={`Filter the table by ${label}`} place="bottom">
                          <input
                            type="search"
                            className="column-filter-input"
                            list={listId}
                            aria-label={`Search ${label}`}
                            placeholder={`Search ${label}`}
                            value={filters[key]}
                            onChange={(e) => updateFilter(key, e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </Tip>
                        <datalist id={listId}>
                          {columnOptions[key].map((option) => (
                            <option key={option} value={option} />
                          ))}
                        </datalist>
                      </th>
                    );
                  })}
                  <th />
                </tr>
              </thead>
              <tbody>
                {filteredJobs.map((job) => (
                  <Tip
                    key={`${job.jobId}-${job.source}`}
                    text="Open quick job details"
                    place="bottom"
                    attach
                  >
                    <tr className="job-row" onClick={() => setSelectedJob(job)}>
                      {COLUMN_FILTERS.map(({ key }) => {
                        const value = getColumnValue(job, key);
                        if (key === 'jobId') {
                          return <JobIdCell key={key} jobId={value} />;
                        }
                        if (key === 'jobDescription') {
                          return (
                            <JobDescriptionCell
                              key={key}
                              value={value}
                              onOpen={() => setEditingJob(job)}
                            />
                          );
                        }
                        if (key === 'status') {
                          return (
                            <JobStatusCell
                              key={key}
                              job={job}
                              onUpdated={handleJobUpdated}
                            />
                          );
                        }
                        if (key === 'fit') {
                          return <FitCell key={key} job={job} />;
                        }
                        if (key === 'analysisStatus') {
                          return <AnalysisStatusCell key={key} job={job} />;
                        }
                        return <td key={key}>{value}</td>;
                      })}
                      <td onClick={(event) => event.stopPropagation()}>
                        {job.url ? (
                          <Tip text="Open the original job posting in a new tab">
                            <a href={job.url} target="_blank" rel="noreferrer">
                              View
                            </a>
                          </Tip>
                        ) : (
                          'n/a'
                        )}
                      </td>
                    </tr>
                  </Tip>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {addingJob && (
        <AddJobModal
          onClose={() => setAddingJob(false)}
          onCreated={handleJobCreated}
        />
      )}

      {selectedJob && !editingJob && (
        <JobDetailModal
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
          onEditDescription={() => {
            setEditingJob(selectedJob);
          }}
          onUpdated={handleJobUpdated}
        />
      )}

      {editingJob && (
        <JobDescriptionModal
          job={editingJob}
          onClose={() => setEditingJob(null)}
          onSaved={(updated) => {
            handleJobUpdated(updated);
            setSelectedJob(updated);
          }}
        />
      )}
    </div>
  );
}

export default function App() {
  return (
    <AdminProvider>
      <Routes>
        <Route path="/" element={<JobsPage />} />
        <Route path="/jobs/:jobId" element={<JobDetailPage />} />
      </Routes>
    </AdminProvider>
  );
}
