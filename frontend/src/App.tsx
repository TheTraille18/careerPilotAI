import { useCallback, useEffect, useMemo, useState } from 'react';
import { Route, Routes, useNavigate } from 'react-router-dom';
import { fetchJobs, createJob, formatTailorSuccessMessage, tailorResume, updateAnalysisStatus, updateJobDescription } from './api/jobs';
import type { AnalysisStatus, JobListing } from './types/job';
import { ANALYSIS_STATUSES } from './types/job';
import JobDetailPage from './pages/JobDetailPage';
import './App.css';

const SOURCE_LABELS: Record<string, string> = {
  linkedin: 'LinkedIn',
  dice: 'Dice',
  indeed: 'Indeed',
  careerbuilder: 'CareerBuilder',
  manual: 'Manual',
};

const JOB_SOURCE_OPTIONS = ['manual', 'linkedin', 'dice', 'indeed', 'careerbuilder'] as const;

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
  { key: 'applied', label: 'Applied' },
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
      return job.status?.trim() || 'Active';
    case 'analysisStatus':
      return normalizeAnalysisStatus(job.analysisStatus);
    case 'applied':
      return job.applied?.trim() || 'No';
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

function AnalysisStatusCell({
  job,
  onUpdated,
}: {
  job: JobListing;
  onUpdated: (job: JobListing) => void;
}) {
  const [saving, setSaving] = useState(false);
  const value = normalizeAnalysisStatus(job.analysisStatus);

  const onChange = async (next: AnalysisStatus) => {
    if (next === value) return;
    setSaving(true);
    try {
      const updated = await updateAnalysisStatus(job.jobId, job.source, next);
      onUpdated(normalizeJob(updated));
    } catch {
      // Keep previous value in the select via controlled value from job state.
    } finally {
      setSaving(false);
    }
  };

  return (
    <td className="analysis-status-cell" onClick={(event) => event.stopPropagation()}>
      <select
        className="analysis-status-select"
        aria-label="Analysis Status"
        value={value}
        disabled={saving}
        onChange={(event) => void onChange(event.target.value as AnalysisStatus)}
      >
        {ANALYSIS_STATUSES.map((status) => (
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
    { label: 'Applied', value: job.applied?.trim() || 'No' },
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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !saving) onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, saving]);

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
            disabled={saving}
            aria-label="Close"
          >
            Close
          </button>
        </div>

        <textarea
          className="job-description-textarea"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Paste the job description here..."
          autoFocus
          spellCheck
        />

        {error && <div className="job-panel-error">{error}</div>}

        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="button" className="btn-primary" onClick={() => void save()} disabled={saving}>
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
    status: job.status?.trim() || 'Active',
    jobDescription: job.jobDescription?.trim() || 'Not available',
    analysisStatus: normalizeAnalysisStatus(job.analysisStatus),
    applied: job.applied?.trim() || 'No',
  };
}

function JobsPage() {
  const [jobs, setJobs] = useState<JobListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<ColumnKey, string>>(EMPTY_FILTERS);
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
      const values = new Set<string>();
      for (const job of jobs) {
        values.add(getColumnValue(job, column.key));
      }
      options[column.key] = Array.from(values).sort((a, b) => a.localeCompare(b));
    }

    return options;
  }, [jobs]);

  const filteredJobs = useMemo(() => {
    return jobs.filter((job) =>
      COLUMN_FILTERS.every(({ key }) => {
        const selected = filters[key];
        if (!selected) return true;
        return getColumnValue(job, key) === selected;
      }),
    );
  }, [jobs, filters]);

  const updateFilter = (key: ColumnKey, value: string) => {
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const clearFilters = () => setFilters(EMPTY_FILTERS);

  const hasActiveFilters = Object.values(filters).some((value) => value !== '');

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
              {!loading && ` · showing ${filteredJobs.length} of ${jobs.length}`}
            </p>
          </div>
          <div className="header-actions">
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
        {error && <div className="job-panel-error">{error}</div>}

        {!loading && !error && jobs.length === 0 && (
          <div className="job-panel-empty">No jobs in DynamoDB yet. Run python gmail.py to import alerts.</div>
        )}

        {!loading && !error && jobs.length > 0 && filteredJobs.length === 0 && (
          <div className="job-panel-empty">No jobs match the current column filters.</div>
        )}

        {(jobs.length > 0 || loading) && (
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
                  {COLUMN_FILTERS.map(({ key, label }) => (
                    <th key={key}>
                      <select
                        aria-label={`Filter ${label}`}
                        value={filters[key]}
                        onChange={(e) => updateFilter(key, e.target.value)}
                      >
                        <option value="">All</option>
                        {columnOptions[key].map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </th>
                  ))}
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
                      if (key === 'analysisStatus') {
                        return (
                          <AnalysisStatusCell
                            key={key}
                            job={job}
                            onUpdated={handleJobUpdated}
                          />
                        );
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
