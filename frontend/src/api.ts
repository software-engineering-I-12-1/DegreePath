export interface ErrorDetail {
  row?: number;
  column?: string;
  value?: unknown;
  field?: string;
  message: string;
}

export class ApiError extends Error {
  status: number;
  code: string;
  errors: Record<string, string>;
  details: ErrorDetail[];
  constructor(
    status: number,
    message: string,
    errors: Record<string, string> = {},
    details: ErrorDetail[] = [],
    code = '',
  ) {
    super(message);
    this.status = status;
    this.errors = errors;
    this.details = details;
    this.code = code;
  }
}

// Called on any 401 so the app can drop the signed-in user and route to /signin (design §5.1).
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

function getCookie(name: string): string | null {
  const match = document.cookie.split('; ').find((row) => row.startsWith(name + '='));
  return match ? decodeURIComponent(match.split('=')[1]) : null;
}

async function ensureCsrf(): Promise<void> {
  if (!getCookie('csrftoken')) {
    await fetch('/api/auth/csrf/', { credentials: 'same-origin' });
  }
}

interface Options {
  method?: string;
  body?: unknown;
}

interface ErrorBody {
  error?: string | { code?: string; message?: string; details?: ErrorDetail[] };
  detail?: string;
  errors?: Record<string, string>;
}

export async function apiFetch<T>(path: string, options: Options = {}): Promise<T | null> {
  const method = options.method ?? 'GET';
  const headers: Record<string, string> = { Accept: 'application/json' };

  if (method !== 'GET') {
    await ensureCsrf();
    if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
    const token = getCookie('csrftoken');
    if (token) headers['X-CSRFToken'] = token;
  }

  const res = await fetch(path, {
    method,
    headers,
    credentials: 'same-origin',
    body:
      options.body instanceof FormData
        ? options.body
        : options.body !== undefined
          ? JSON.stringify(options.body)
          : undefined,
  });

  if (res.status === 204) return null;

  let data: ErrorBody | null = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    if (res.status === 401) onUnauthorized?.();

    const err = data && typeof data.error === 'object' && data.error !== null ? data.error : null;
    const message =
      typeof data?.error === 'string'
        ? data.error
        : err?.message ?? data?.detail ?? `Request failed (${res.status})`;
    const details = err?.details ?? [];
    const errors: Record<string, string> = { ...(data?.errors ?? {}) };
    for (const d of details) {
      if (d.field && !errors[d.field]) errors[d.field] = d.message;
    }
    throw new ApiError(res.status, message, errors, details, err?.code ?? '');
  }
  return data as T;
}