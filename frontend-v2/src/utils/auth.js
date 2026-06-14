/**
 * JWT storage + decoding helpers (T1).
 *
 * The token lives in BOTH localStorage (axios interceptor reads it) and a
 * non-HttpOnly cookie (Next.js middleware reads it for route guards, F2).
 * Keep the two in sync through saveToken/clearToken only.
 */

export const TOKEN_KEY = 'agentfarm_token';

function isBrowser() {
  return typeof window !== 'undefined';
}

export function saveToken(token, maxAgeSeconds = 24 * 3600) {
  if (!isBrowser()) return;
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* localStorage disabled */
  }
  document.cookie = `${TOKEN_KEY}=${token}; path=/; max-age=${maxAgeSeconds}; SameSite=Lax`;
}

export function readToken() {
  if (!isBrowser()) return null;
  try {
    const fromStorage = window.localStorage.getItem(TOKEN_KEY);
    if (fromStorage) return fromStorage;
  } catch {
    /* fall through to cookie */
  }
  const match = document.cookie.match(new RegExp(`(?:^|; )${TOKEN_KEY}=([^;]*)`));
  return match ? match[1] : null;
}

export function clearToken() {
  if (!isBrowser()) return;
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0; SameSite=Lax`;
}

/** Decode a JWT payload without verifying (display only — the backend verifies). */
export function decodeJwt(token) {
  try {
    const payload = token.split('.')[1];
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

/** Current user {phone, role, entity_id, name} from the stored token, or null. */
export function getStoredUser() {
  const token = readToken();
  if (!token) return null;
  const claims = decodeJwt(token);
  if (!claims) return null;
  if (claims.exp && claims.exp * 1000 < Date.now()) {
    clearToken();
    return null;
  }
  return {
    phone: claims.sub,
    role: claims.role,
    entityId: claims.entity_id ?? null,
    name: claims.name ?? null,
  };
}
