import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { apiFetch, setUnauthorizedHandler } from '../api';

export interface User {
  id: number;
  email: string;
  is_staff: boolean;
  user_id?: number;
  role?: 'student' | 'admin';
  profile_id?: string;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  register: (email: string, password: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Any 401 (e.g. the 24h session expired with the tab open) clears the user;
    // ProtectedRoute then redirects to /signin.
    setUnauthorizedHandler(() => setUser(null));
    return () => setUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    apiFetch<User>('/api/auth/me/')
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    setUser(await apiFetch<User>('/api/auth/register/', { method: 'POST', body: { email, password } }));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setUser(await apiFetch<User>('/api/auth/login/', { method: 'POST', body: { email, password } }));
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiFetch('/api/auth/logout/', { method: 'POST' });
    } catch {
      // already signed out (expired session): fall through and clear the user
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, register, login, logout }),
    [user, loading, register, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}