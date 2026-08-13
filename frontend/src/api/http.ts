/** Shared fetch defaults: send session cookie for admin SSO. */

/** API origin for production (ALB). Empty in local Vite → same-origin `/api` proxy. */
export function getApiBaseUrl(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || '';
  return raw.replace(/\/$/, '');
}

/** Prefix relative `/api/...` paths with the configured API base URL. */
export function apiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const base = getApiBaseUrl();
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return base ? `${base}${normalized}` : normalized;
}

export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  return fetch(apiUrl(input), {
    ...init,
    headers,
    credentials: 'include',
  });
}

export async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (typeof payload.detail === 'string' && payload.detail) return payload.detail;
  } catch {
    // fall through
  }
  const body = await response.text();
  return body || `Request failed (${response.status})`;
}
