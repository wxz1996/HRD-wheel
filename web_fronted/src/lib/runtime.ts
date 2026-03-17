const DEFAULT_API_BASE = 'http://localhost:8000';

export function getApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE?.trim() || DEFAULT_API_BASE;
  return base.endsWith('/') ? base.slice(0, -1) : base;
}

export function getWsBase(): string {
  const apiBase = getApiBase();
  const url = new URL(apiBase);
  const wsProto = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${wsProto}//${url.host}/ws`;
}

export function getAuthToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return localStorage.getItem('hrt_token');
}

export function authHeaders(token: string | null): HeadersInit {
  if (!token) {
    return {};
  }
  return { Authorization: `Bearer ${token}` };
}
