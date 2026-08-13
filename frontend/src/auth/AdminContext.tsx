import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { apiFetch, apiUrl, readErrorMessage } from '../api/http';

export type AdminStatus = {
  authEnabled: boolean;
  isAdmin: boolean;
  email: string | null;
};

type AdminContextValue = AdminStatus & {
  loading: boolean;
  canEdit: boolean;
  refresh: () => Promise<void>;
  login: () => void;
  logout: () => Promise<void>;
};

const AdminContext = createContext<AdminContextValue | null>(null);

const DEFAULT_STATUS: AdminStatus = {
  authEnabled: false,
  isAdmin: true,
  email: null,
};

export function AdminProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AdminStatus>(DEFAULT_STATUS);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const response = await apiFetch('/api/admin/status');
      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }
      const data = (await response.json()) as AdminStatus;
      setStatus({
        authEnabled: Boolean(data.authEnabled),
        isAdmin: Boolean(data.isAdmin),
        email: data.email ?? null,
      });
    } catch {
      // If status fails, keep UI usable only when auth is off locally.
      setStatus(DEFAULT_STATUS);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('admin') === '1') {
      params.delete('admin');
      const next = `${window.location.pathname}${params.toString() ? `?${params}` : ''}`;
      window.history.replaceState({}, '', next);
      void refresh();
    }
  }, [refresh]);

  const login = useCallback(() => {
    window.location.href = apiUrl('/api/admin/login');
  }, []);

  const logout = useCallback(async () => {
    await apiFetch('/api/admin/logout', { method: 'POST' });
    await refresh();
  }, [refresh]);

  const value = useMemo<AdminContextValue>(() => {
    const canEdit = !status.authEnabled || status.isAdmin;
    return {
      ...status,
      loading,
      canEdit,
      refresh,
      login,
      logout,
    };
  }, [status, loading, refresh, login, logout]);

  return <AdminContext.Provider value={value}>{children}</AdminContext.Provider>;
}

export function useAdmin(): AdminContextValue {
  const ctx = useContext(AdminContext);
  if (!ctx) {
    throw new Error('useAdmin must be used within AdminProvider');
  }
  return ctx;
}
