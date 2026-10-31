export class ApiError extends Error {
  status: number;
  errors: Record<string, string>;
  details: { row?: number; column?: string; value?: unknown; message: string }[];
  constructor(status: number, message: string, errors: Record<string, string> = {}, details: ApiError['details'] = []) {
    super(message);
    this.status = status;
    this.errors = errors;
    this.details = details;
  }
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
    body: options.body instanceof FormData ? options.body : options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (res.status === 204) return null;

  let data: { error?: string | { message: string; details?: ApiError['details'] }; detail?: string; errors?: Record<string, string> } | null = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    throw new ApiError(
      res.status,
      typeof data?.error === 'string' ? data.error : data?.error?.message ?? data?.detail ?? `Request failed (${res.status})`,
      data?.errors ?? {},
      typeof data?.error === 'object' ? data.error.details ?? [] : [],
    );
  }
  return data as T;
}
