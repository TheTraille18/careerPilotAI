import { useCallback, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  checkJobFit,
  downloadCoverLetter,
  downloadTailoredResume,
  fetchJob,
  fetchJobDescriptionText,
  formatCoverLetterSuccessMessage,
  formatTailorSuccessMessage,
  generateCoverLetter,
  tailorResume,
  updateJobStatus,
} from '../api/jobs';
import type { AnalysisStatus, EvalResult, FitStatus, JobListing, JobStatus } from '../types/job';
import { ANALYSIS_STATUSES, FIT_STATUSES, JOB_STATUSES } from '../types/job';
import { useAdmin } from '../auth/AdminContext';
import ProfileButton from '../components/ProfileButton';
import DemoModeBanner from '../components/DemoModeBanner';
import Tip from '../components/Tip';
import '../App.css';

const SOURCE_LABELS: Record<string, string> = {
  linkedin: 'LinkedIn',
  dice: 'Dice',
  indeed: 'Indeed',
  careerbuilder: 'CareerBuilder',
  remoterocketship: 'Remote Rocketship',
  aiapply: 'AIApply',
  manual: 'Manual',
};

const SCORE_LABELS: { key: keyof NonNullable<EvalResult['scores']>; label: string }[] = [
  { key: 'grounding', label: 'Grounding' },
  { key: 'ruleCompliance', label: 'Rule compliance' },
  { key: 'jobFit', label: 'Job fit' },
  { key: 'minimalChange', label: 'Minimal change' },
  { key: 'readability', label: 'Readability' },
];

function formatDate(value: string): string {
  if (!value) return 'n/a';
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value;
  return new Date(parsed).toLocaleString();
}

function formatAppliedDate(value: string | undefined): string {
  const text = value?.trim() || '';
  if (!text) return '';
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    const [year, month, day] = text.split('-').map(Number);
    return new Date(year, month - 1, day).toLocaleDateString();
  }
  const parsed = Date.parse(text);
  if (Number.isNaN(parsed)) return text;
  return new Date(parsed).toLocaleDateString();
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

function normalizeJob(job: JobListing): JobListing {
  return {
    ...job,
    status: normalizeJobStatus(job.status),
    jobDescription: job.jobDescription?.trim() || 'Not available',
    analysisStatus: normalizeAnalysisStatus(job.analysisStatus),
    applied: job.applied?.trim() || 'No',
    appliedDate: job.appliedDate?.trim() || '',
    evalResult: job.evalResult ?? null,
    fit: normalizeFitStatus(job.fit),
    fitReason: job.fitReason?.trim() || '',
    fitCheckedAt: job.fitCheckedAt?.trim() || '',
  };
}

function tokenizeWords(text: string): string[] {
  return text.match(/\s+|[^\s]+/g) ?? [];
}

type DiffToken = { text: string; type: 'equal' | 'add' | 'del' };

/** Word-level LCS diff for before/after highlighting. */
function diffWords(before: string, after: string): DiffToken[] {
  const a = tokenizeWords(before);
  const b = tokenizeWords(after);
  const n = a.length;
  const m = b.length;
  const dp: number[][] = Array.from({ length: n + 1 }, () => Array(m + 1).fill(0));

  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const tokens: DiffToken[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      tokens.push({ text: a[i], type: 'equal' });
      i += 1;
      j += 1;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      tokens.push({ text: a[i], type: 'del' });
      i += 1;
    } else {
      tokens.push({ text: b[j], type: 'add' });
      j += 1;
    }
  }
  while (i < n) {
    tokens.push({ text: a[i], type: 'del' });
    i += 1;
  }
  while (j < m) {
    tokens.push({ text: b[j], type: 'add' });
    j += 1;
  }
  return tokens;
}

function HighlightedDiff({
  before,
  after,
  mode,
}: {
  before: string;
  after: string;
  mode: 'before' | 'after';
}) {
  const tokens = diffWords(before, after);
  const visible =
    mode === 'before'
      ? tokens.filter((token) => token.type !== 'add')
      : tokens.filter((token) => token.type !== 'del');

  return (
    <span className="eval-diff-text">
      {visible.map((token, index) => {
        if (token.type === 'equal') {
          return <span key={index}>{token.text}</span>;
        }
        return (
          <mark
            key={index}
            className={token.type === 'add' ? 'eval-diff-add' : 'eval-diff-del'}
          >
            {token.text}
          </mark>
        );
      })}
    </span>
  );
}

function EvalResultPanel({ result }: { result: EvalResult }) {
  const passed = result.pass === true;
  const scores = result.scores ?? {};

  return (
    <section className={`eval-result-panel ${passed ? 'eval-pass' : 'eval-fail'}`}>
      <div className="eval-result-header">
        <h3>Resume eval</h3>
        <span className={`eval-badge ${passed ? 'pass' : 'fail'}`}>
          {passed ? 'PASS' : 'FAIL'}
        </span>
        {typeof result.overallScore === 'number' && (
          <span className="eval-overall">
            Overall {result.overallScore}/25
            {` · ${Math.round((result.overallScore / 25) * 100)}%`}
          </span>
        )}
        {typeof result.changedParagraphCount === 'number' && (
          <span className="eval-meta">{result.changedParagraphCount} paragraphs changed</span>
        )}
        {result.evaluatedAt && (
          <span className="eval-meta">Last run {formatDate(result.evaluatedAt)}</span>
        )}
      </div>

      <p className="eval-compare-note">
        Compares tailored resume vs job description and vs original resume.
      </p>

      {result.summary && <p className="eval-summary">{result.summary}</p>}

      <div className="eval-score-grid">
        {SCORE_LABELS.map(({ key, label }) => (
          <div key={key} className="eval-score-item">
            <span className="eval-score-label">{label}</span>
            <span className="eval-score-value">
              {typeof scores[key] === 'number' ? `${scores[key]}/5` : '—'}
            </span>
          </div>
        ))}
      </div>

      {!!result.hardFails?.length && (
        <div className="eval-section">
          <h4>Hard fails</h4>
          <ul>
            {result.hardFails.map((item, index) => (
              <li key={`${item}-${index}`}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {!!result.changes?.length && (
        <div className="eval-section">
          <h4>Changes</h4>
          <ul className="eval-changes">
            {result.changes.map((change, index) => {
              const before = change.originalText?.trim() || '';
              const after = change.newText?.trim() || '';
              return (
                <li key={`${change.paragraphId ?? 'c'}-${index}`}>
                  <strong>
                    {[change.paragraphId, change.operation].filter(Boolean).join(' · ') ||
                      'Change'}
                  </strong>
                  {change.reason && (
                    <p className="eval-change-reason">
                      <span className="eval-change-label">Reason:</span> {change.reason}
                    </p>
                  )}
                  {change.operation === 'delete' ? (
                    before ? (
                      <blockquote className="eval-change-before">
                        <span className="eval-change-label">Removed:</span>{' '}
                        <mark className="eval-diff-del">{before}</mark>
                      </blockquote>
                    ) : null
                  ) : (
                    <>
                      {before && (
                        <blockquote className="eval-change-before">
                          <span className="eval-change-label">Before:</span>{' '}
                          {after ? (
                            <HighlightedDiff before={before} after={after} mode="before" />
                          ) : (
                            <mark className="eval-diff-del">{before}</mark>
                          )}
                        </blockquote>
                      )}
                      {after && (
                        <blockquote className="eval-change-after">
                          <span className="eval-change-label">After:</span>{' '}
                          {before ? (
                            <HighlightedDiff before={before} after={after} mode="after" />
                          ) : (
                            <mark className="eval-diff-add">{after}</mark>
                          )}
                        </blockquote>
                      )}
                    </>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {!!result.violations?.length && (
        <div className="eval-section">
          <h4>Violations</h4>
          <ul className="eval-violations">
            {result.violations.map((violation, index) => (
              <li key={`${violation.paragraphId ?? 'v'}-${index}`}>
                <strong>
                  {[violation.paragraphId, violation.type].filter(Boolean).join(' · ') ||
                    'Violation'}
                </strong>
                {violation.quote && <blockquote>{violation.quote}</blockquote>}
                {violation.explanation && <p>{violation.explanation}</p>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function ViewJobDescriptionModal({
  job,
  onClose,
}: {
  job: JobListing;
  onClose: () => void;
}) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void (async () => {
      try {
        const body = await fetchJobDescriptionText(job.jobId, job.source);
        if (!cancelled) setText(body);
      } catch (err) {
        if (!cancelled) {
          setText('');
          setError(err instanceof Error ? err.message : 'Failed to load job description');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [job.jobId, job.source]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="modal-panel job-description-view-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="view-job-description-title"
      >
        <div className="modal-header">
          <div>
            <h2 id="view-job-description-title">Job Description</h2>
            <p>
              {job.title || 'Untitled'}
              {job.company ? ` · ${job.company}` : ''}
            </p>
          </div>
          <Tip text="Close the job description viewer">
            <button
              type="button"
              className="btn-secondary modal-close"
              onClick={onClose}
              aria-label="Close"
            >
              Close
            </button>
          </Tip>
        </div>

        {loading && <div className="job-panel-empty">Loading description...</div>}
        {error && <div className="job-panel-error">{error}</div>}
        {!loading && !error && (
          <pre className="job-description-view-text">{text}</pre>
        )}

        <div className="modal-actions">
          <Tip text="Close the job description viewer">
            <button type="button" className="btn-primary" onClick={onClose}>
              Close
            </button>
          </Tip>
        </div>
      </div>
    </div>
  );
}

export default function JobDetailPage() {
  const { jobId = '' } = useParams<{ jobId: string }>();
  const [searchParams] = useSearchParams();
  const source = searchParams.get('source')?.trim() || '';
  const { canEdit, authEnabled, isAdmin } = useAdmin();

  const [job, setJob] = useState<JobListing | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tailorError, setTailorError] = useState<string | null>(null);
  const [tailorSuccess, setTailorSuccess] = useState<string | null>(null);
  const [tailoring, setTailoring] = useState(false);
  const [generatingCoverLetter, setGeneratingCoverLetter] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadingCoverLetter, setDownloadingCoverLetter] = useState(false);
  const [savingStatus, setSavingStatus] = useState(false);
  const [checkingFit, setCheckingFit] = useState(false);
  const [viewingDescription, setViewingDescription] = useState(false);

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
        { label: 'Fit', value: normalizeFitStatus(job.fit) },
        { label: 'Fit reason', value: job.fitReason?.trim() || 'n/a' },
        { label: 'Job Description', value: job.jobDescription },
        { label: 'Analysis Status', value: normalizeAnalysisStatus(job.analysisStatus) },
        { label: 'Applied', value: formatAppliedDate(job.appliedDate) || job.applied },
        { label: 'Date', value: formatDate(job.date) },
        { label: 'Email ID', value: job.emailId || 'n/a' },
        { label: 'Updated At', value: job.updatedAt ? formatDate(job.updatedAt) : 'n/a' },
      ]
    : [];

  const statusValue = job ? normalizeJobStatus(job.status) : 'Active';
  const analysisStatus = job ? normalizeAnalysisStatus(job.analysisStatus) : 'Pending';
  const desc = job?.jobDescription?.trim() || 'Not available';
  const hasDescription =
    !!job && (desc === 'Available' || (desc !== 'Not available' && desc.length >= 40));
  const canDownloadResume =
    !!job && (analysisStatus === 'Tailored Resume' || analysisStatus === 'Cover Letter');
  const canGenerateCoverLetter =
    !!job && (analysisStatus === 'Tailored Resume' || analysisStatus === 'Cover Letter');
  const canDownloadCoverLetter = !!job && analysisStatus === 'Cover Letter';
  const busy =
    tailoring ||
    generatingCoverLetter ||
    downloading ||
    downloadingCoverLetter ||
    savingStatus ||
    checkingFit;

  const onCheckFit = async () => {
    if (!job || !hasDescription) {
      setTailorError('Paste and save a job description before checking fit');
      setTailorSuccess(null);
      return;
    }
    setCheckingFit(true);
    setTailorError(null);
    setTailorSuccess(null);
    try {
      const pasted = desc === 'Available' || desc === 'Not available' ? '' : desc;
      const result = await checkJobFit(job.jobId, job.source, pasted);
      const updated = normalizeJob(result.job);
      setJob(updated);
      setTailorSuccess(`${updated.fit}: ${updated.fitReason || 'No reason provided.'}`);
    } catch (err) {
      setTailorError(err instanceof Error ? err.message : 'Fit check failed');
      setTailorSuccess(null);
    } finally {
      setCheckingFit(false);
    }
  };

  const onStatusChange = async (next: JobStatus) => {
    if (!job || next === statusValue) return;
    setSavingStatus(true);
    setTailorError(null);
    try {
      const updated = await updateJobStatus(job.jobId, job.source, next);
      setJob(normalizeJob(updated));
    } catch (err) {
      setTailorError(err instanceof Error ? err.message : 'Failed to update Status');
    } finally {
      setSavingStatus(false);
    }
  };

  const onDownloadResume = async () => {
    if (!job) return;
    setDownloading(true);
    setTailorError(null);
    try {
      await downloadTailoredResume(job.jobId);
    } catch (err) {
      setTailorError(err instanceof Error ? err.message : 'Failed to download tailored resume');
    } finally {
      setDownloading(false);
    }
  };

  const onDownloadCoverLetter = async () => {
    if (!job) return;
    setDownloadingCoverLetter(true);
    setTailorError(null);
    try {
      await downloadCoverLetter(job.jobId);
    } catch (err) {
      setTailorError(err instanceof Error ? err.message : 'Failed to download cover letter');
    } finally {
      setDownloadingCoverLetter(false);
    }
  };

  const onGenerateCoverLetter = async () => {
    if (!job) return;
    if (job.jobDescription?.trim() !== 'Available') {
      setTailorError('Job description is not available. Paste and save a description first.');
      setTailorSuccess(null);
      return;
    }

    setGeneratingCoverLetter(true);
    setTailorError(null);
    setTailorSuccess(null);
    try {
      const result = await generateCoverLetter(job);
      setJob(normalizeJob(result.job));
      setTailorSuccess(formatCoverLetterSuccessMessage(result.s3));
    } catch (err) {
      setTailorError(err instanceof Error ? err.message : 'Failed to generate cover letter');
      setTailorSuccess(null);
    } finally {
      setGeneratingCoverLetter(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="page-header">
        <div className="page-header-top">
          <div>
            <h1>
              Job details
              {authEnabled && !isAdmin ? <span className="demo-title-badge">Demo</span> : null}
            </h1>
            <p>
              {authEnabled && !isAdmin
                ? 'Restricted preview — sample job data'
                : `Loaded from GET /api/jobs/{'{job_id}'}?source=...`}
            </p>
          </div>
          <div className="header-actions">
            <Tip text="Return to the main jobs table">
              <Link to="/" className="btn-secondary link-button">
                Back to jobs
              </Link>
            </Tip>
            <Tip text="Reload this job from the server">
              <button
                type="button"
                className="icon-action-button"
                onClick={() => void loadJob()}
                disabled={loading}
                aria-label={loading ? 'Refreshing job' : 'Refresh job'}
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
        <DemoModeBanner />
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
                {job.location ? ` · ${job.location}` : ''}
              </p>
              {job.url ? (
                <p>
                  <Tip text="Open the original job posting in a new tab">
                    <a href={job.url} target="_blank" rel="noreferrer">
                      Open job posting
                    </a>
                  </Tip>
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
              <div className="job-detail-row">
                <dt>Status</dt>
                <dd>
                  <Tip
                    text={
                      canEdit
                        ? 'Change this job’s pipeline status'
                        : 'Admin sign-in required to change status'
                    }
                  >
                    <select
                      className="job-status-select"
                      aria-label="Status"
                      value={statusValue}
                      disabled={savingStatus || busy || !canEdit}
                      onChange={(event) => void onStatusChange(event.target.value as JobStatus)}
                    >
                      {JOB_STATUSES.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </Tip>
                </dd>
              </div>
            </dl>

            {job.evalResult && <EvalResultPanel result={job.evalResult} />}

            {tailorError && <div className="job-panel-error">{tailorError}</div>}
            {tailorSuccess && <div className="job-panel-success">{tailorSuccess}</div>}

            <div className="job-full-detail-actions">
              <Tip
                text={
                  hasDescription
                    ? 'Open a modal with the full job description text'
                    : 'No job description is available to view yet'
                }
              >
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!hasDescription || busy}
                  onClick={() => setViewingDescription(true)}
                >
                  View description
                </button>
              </Tip>
              <Tip
                text={
                  !canEdit
                    ? 'Admin sign-in required for AI fit checks'
                    : hasDescription
                      ? 'Run AI fit scoring for this job'
                      : 'Add a job description before checking fit'
                }
              >
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!hasDescription || busy || !canEdit}
                  onClick={() => void onCheckFit()}
                >
                  {checkingFit ? 'Checking fit...' : 'Check fit'}
                </button>
              </Tip>
              <Tip
                text={
                  canDownloadResume
                    ? 'Download the tailored resume .docx for this job'
                    : 'Tailor a resume first to enable download'
                }
              >
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!canDownloadResume || busy}
                  onClick={() => void onDownloadResume()}
                >
                  {downloading ? 'Downloading...' : 'Download Tailored Resume'}
                </button>
              </Tip>
              <Tip
                text={
                  canDownloadCoverLetter
                    ? 'Download the generated cover letter .docx'
                    : 'Generate a cover letter first to enable download'
                }
              >
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!canDownloadCoverLetter || busy}
                  onClick={() => void onDownloadCoverLetter()}
                >
                  {downloadingCoverLetter ? 'Downloading...' : 'Download Cover Letter'}
                </button>
              </Tip>
              <Tip
                text={
                  !canEdit
                    ? 'Admin sign-in required'
                    : canGenerateCoverLetter
                      ? 'Generate a cover letter with AI for this job'
                      : 'Tailor a resume first to generate a cover letter'
                }
              >
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!canGenerateCoverLetter || busy || !canEdit}
                  onClick={() => void onGenerateCoverLetter()}
                >
                  {generatingCoverLetter ? 'Generating cover letter...' : 'Generate Cover Letter'}
                </button>
              </Tip>
              <Tip
                text={
                  canEdit
                    ? 'Tailor the resume with AI and run the automatic eval'
                    : 'Admin sign-in required to tailor resumes'
                }
              >
                <button
                  type="button"
                  className="btn-primary"
                  disabled={busy || !canEdit}
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
                      setJob(
                        normalizeJob({
                          ...result.job,
                          evalResult: result.job.evalResult ?? result.eval ?? null,
                        }),
                      );
                      setTailorSuccess(
                        `${formatTailorSuccessMessage(result.s3)} Eval completed.`,
                      );
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
                {tailoring ? 'Tailoring & evaluating...' : 'Tailor Resume'}
              </button>
              </Tip>
            </div>
          </section>
        )}
      </main>

      {viewingDescription && job && (
        <ViewJobDescriptionModal job={job} onClose={() => setViewingDescription(false)} />
      )}
    </div>
  );
}
