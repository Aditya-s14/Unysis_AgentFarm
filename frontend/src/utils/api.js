/**
 * Generic API helper utilities shared by the axios client and hooks.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

/**
 * Join a base URL and a path without producing duplicate slashes.
 */
export function buildUrl(base, path) {
  if (!base) return path;
  if (!path) return base;
  const b = base.endsWith('/') ? base.slice(0, -1) : base;
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${b}${p}`;
}

/**
 * Convert an axios error into a human-friendly message for surfaces to display.
 */
export function formatApiError(error) {
  if (!error) return 'Unknown error';
  if (error.response) {
    const { status, data } = error.response;
    const detail = data?.detail || data?.message || data?.error;
    return `[${status}] ${detail || 'Request failed'}`;
  }
  if (error.request) {
    return 'No response from server. Is the backend running?';
  }
  return error.message || 'Request setup failed';
}
