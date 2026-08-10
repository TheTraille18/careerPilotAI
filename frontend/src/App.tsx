import { useCallback, useEffect, useMemo, useState } from 'react';
import { Route, Routes, useNavigate } from 'react-router-dom';
import { fetchJobs, createJob, formatTailorSuccessMessage, tailorResume, updateJobStatus, updateJobDescription, fetchJobDescriptionFromUrl } from './api/jobs';
import type { AnalysisStatus, JobListing, JobStatus } from './types/job';
import { ANALYSIS_STATUSES, JOB_STATUSES } from './types/job';
import JobDetailPage from './pages/JobDetailPage';
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
  analysisStatus: '',
  applied: '',
  date: '',
};

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
    <td className="job-id-cell" title={jobId} onClick={(event) => event.stopPropagation()}>
      <div className="job-id-row">
        <button
          type="button"
          className={`copy-job-id${copied ? ' copied' : ''}`}
          onClick={() => void copyJobId()}
          aria-label={copied ? 'Job ID copied' : 'Copy Job ID'}
          title={copied ? 'Copied!' : 'Copy Job ID'}
        >
          {copied ? <CheckIcon /> : <CopyIcon />}
        </button>
        <span className="job-id-text">{jobId}</span>
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
  return (
    <td className="job-description-cell" onClick={(event) => event.stopPropagation()}>
      <button
        type="button"
        className="job-description-trigger"
        onClick={onOpen}
        title="Click to paste or edit job description"
      >
        {value}
      </button>
    </td>
  );
}

function AnalysisStatusCell({ job }: { job: JobListing }) {
  return (
    <td className="analysis-status-cell">{normalizeAnalysisStatus(job.analysisStatus)}</td>
  );
}

function JobStatusCell({
  job,
  onUpdated,
}: {
  job: JobListing;
  onUpdated: (job: JobListing) => void;
}) {
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
      <select
        className="job-status-select"
        aria-label="Status"
        value={value}
        disabled={saving}
        onChange={(event) => void onChange(event.target.value as JobStatus)}
      >
        {JOB_STATUSES.map((status) => (
          <option key={status} value={status}>
            {status}
          </option>
        ))}
      </select>
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
          <button
            type="button"
            className="btn-secondary modal-close"
            onClick={onClose}
            disabled={saving}
            aria-label="Close"
          >
            Close
          </button>
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
          <button type="button" className="btn-secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="button" className="btn-primary" onClick={() => void save()} disabled={saving}>
            {saving ? 'Adding...' : 'Add Job'}
          </button>
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
  const [tailorError, setTailorError] = useState<string | null>(null);
  const [tailorSuccess, setTailorSuccess] = useState<string | null>(null);
  const [tailoring, setTailoring] = useState(false);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !tailoring) onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, tailoring]);

  const fields: { label: string; value: string }[] = [
    { label: 'Job ID', value: job.jobId || 'n/a' },
    { label: 'Title', value: job.title || 'n/a' },
    { label: 'Company', value: job.company || 'n/a' },
    { label: 'Location', value: job.location || 'n/a' },
    { label: 'Source', value: SOURCE_LABELS[job.source] ?? job.source ?? 'n/a' },
    { label: 'Status', value: job.status?.trim() || 'Active' },
    { label: 'Job Description', value: job.jobDescription?.trim() || 'Not available' },
    { label: 'Analysis Status', value: normalizeAnalysisStatus(job.analysisStatus) },
    { label: 'Applied', value: formatAppliedDate(job.appliedDate) || job.applied?.trim() || 'No' },
    { label: 'Date', value: formatDate(job.date) },
  ];

  const openFullDetails = () => {
    const params = new URLSearchParams({ source: job.source });
    navigate(`/jobs/${encodeURIComponent(job.jobId)}?${params}`);
  };

  const onTailorResume = async () => {
    if (job.jobDescription?.trim() !== 'Available') {
      setTailorError('Job description is not available. Paste and save a description first.');
      setTailorSuccess(null);
      return;
    }

    setTailoring(true);
    setTailorError(null);
    setTailorSuccess(null);
    try {
      const result = await tailorResume(job);
      onUpdated(normalizeJob(result.job));
      setTailorSuccess(formatTailorSuccessMessage(result.s3));
    } catch (err) {
      setTailorError(err instanceof Error ? err.message : 'Failed to tailor resume');
      setTailorSuccess(null);
    } finally {
      setTailoring(false);
    }
  };

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
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
          <button type="button" className="btn-secondary modal-close" onClick={onClose} aria-label="Close">
            Close
          </button>
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
                <a href={job.url} target="_blank" rel="noreferrer">
                  Open job posting
                </a>
              ) : (
                'n/a'
              )}
            </dd>
          </div>
        </dl>

        {tailorError && <div className="job-panel-error">{tailorError}</div>}
        {tailorSuccess && <div className="job-panel-success">{tailorSuccess}</div>}

        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={onEditDescription}>
            Edit description
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => void onTailorResume()}
            disabled={tailoring}
          >
            {tailoring ? 'Tailoring...' : 'Tailor Resume'}
          </button>
          <button type="button" className="btn-primary" onClick={openFullDetails}>
            Full details
          </button>
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
  const initial =
    job.jobDescription?.trim() === 'Not available' ||
    job.jobDescription?.trim() === 'Available'
      ? ''
      : (job.jobDescription ?? '');
  const [text, setText] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !saving && !fetching) onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, saving, fetching]);

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
                <a href={job.url} target="_blank" rel="noreferrer">
                  Open job posting
                </a>
              </p>
            ) : (
              <p className="modal-job-link muted">No job URL available</p>
            )}
          </div>
          <button
            type="button"
            className="btn-secondary modal-close"
            onClick={onClose}
            disabled={saving || fetching}
            aria-label="Close"
          >
            Close
          </button>
        </div>

        <textarea
          className="job-description-textarea"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Paste the job description here, or fetch from the public job URL..."
          autoFocus
          spellCheck
          disabled={saving || fetching}
        />

        {error && <div className="job-panel-error">{error}</div>}

        <div className="modal-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => void fetchFromUrl()}
            disabled={saving || fetching || !job.url?.trim()}
            title={job.url ? 'Try fetching a public job posting URL' : 'No job URL on this listing'}
          >
            {fetching ? 'Fetching...' : 'Fetch from URL'}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={onClose}
            disabled={saving || fetching}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => void save()}
            disabled={saving || fetching}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
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
  };
}

function JobsPage() {
  const [jobs, setJobs] = useState<JobListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<ColumnKey, string>>(EMPTY_FILTERS);
  const [globalSearch, setGlobalSearch] = useState('');
  const [activeTab, setActiveTab] = useState<'active' | 'applied' | 'interview' | 'inactive'>('active');
  const [editingJob, setEditingJob] = useState<JobListing | null>(null);
  const [selectedJob, setSelectedJob] = useState<JobListing | null>(null);
  const [addingJob, setAddingJob] = useState(false);

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
      const values = new Set<string>();
      for (const job of jobs) {
        values.add(getColumnValue(job, column.key));
      }
      options[column.key] = Array.from(values).sort((a, b) => a.localeCompare(b));
    }

    return options;
  }, [jobs]);

  const tabOf = useCallback((job: JobListing): 'active' | 'applied' | 'interview' | 'inactive' => {
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

  return (
    <div className="app-shell">
      <header className="page-header">
        <div className="page-header-top">
          <div>
            <h1>CareerPilot AI</h1>
            <p>
              Jobs from DynamoDB
              {!loading && ` · showing ${filteredJobs.length} of ${tabJobs.length}`}
            </p>
          </div>
          <div className="header-actions">
            <input
              type="search"
              className="global-search-input"
              aria-label="Search all columns"
              placeholder="Search all columns..."
              value={globalSearch}
              onChange={(e) => setGlobalSearch(e.target.value)}
            />
            <button
              type="button"
              className="btn-add-job"
              onClick={() => setAddingJob(true)}
              aria-label="Add job"
              title="Add job"
            >
              +
            </button>
            {hasActiveFilters && (
              <button type="button" className="btn-secondary" onClick={clearFilters}>
                Clear filters
              </button>
            )}
            <button type="button" className="btn-primary" onClick={() => void loadJobs()} disabled={loading}>
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>
      </header>

      <main className="page-main">
        <div className="job-tabs" role="tablist" aria-label="Job status tabs">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'active'}
            className={`job-tab${activeTab === 'active' ? ' active' : ''}`}
            onClick={() => setActiveTab('active')}
          >
            Active ({tabCounts.active})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'applied'}
            className={`job-tab${activeTab === 'applied' ? ' active' : ''}`}
            onClick={() => setActiveTab('applied')}
          >
            Applied ({tabCounts.applied})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'interview'}
            className={`job-tab${activeTab === 'interview' ? ' active' : ''}`}
            onClick={() => setActiveTab('interview')}
          >
            Interview ({tabCounts.interview})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'inactive'}
            className={`job-tab${activeTab === 'inactive' ? ' active' : ''}`}
            onClick={() => setActiveTab('inactive')}
          >
            Inactive ({tabCounts.inactive})
          </button>
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
                  <tr
                    key={`${job.jobId}-${job.source}`}
                    className="job-row"
                    onClick={() => setSelectedJob(job)}
                  >
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
                      if (key === 'analysisStatus') {
                        return <AnalysisStatusCell key={key} job={job} />;
                      }
                      return <td key={key}>{value}</td>;
                    })}
                    <td onClick={(event) => event.stopPropagation()}>
                      {job.url ? (
                        <a href={job.url} target="_blank" rel="noreferrer">
                          View
                        </a>
                      ) : (
                        'n/a'
                      )}
                    </td>
                  </tr>
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
    <Routes>
      <Route path="/" element={<JobsPage />} />
      <Route path="/jobs/:jobId" element={<JobDetailPage />} />
    </Routes>
  );
}
