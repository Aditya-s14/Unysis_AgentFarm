import { NextResponse } from 'next/server';

/**
 * Role-based route guard (F2).
 *
 * Reads the JWT from the `agentfarm_token` cookie (set by login, T1) and
 * enforces which roles may open which routes. Claims are decoded, not
 * cryptographically verified — the backend verifies every API call; this
 * layer only decides navigation. Wrong role → redirect to that role's own
 * home (the PDF allows "403 or redirect"); no/expired token → /login.
 */

const TOKEN_COOKIE = 'agentfarm_token';

// FPO is the command center and may open everything.
const ACCESS = {
  '/dashboard': ['fpo'],
  '/scenario': ['fpo'],
  '/runs': ['fpo'],
  '/advisor': ['fpo', 'farmer'],
  '/farmer': ['fpo', 'farmer'],
  '/driver': ['fpo', 'driver'],
  '/mandi': ['fpo', 'mandi'],
};

const ROLE_HOME = {
  fpo: '/dashboard',
  farmer: '/farmer',
  driver: '/driver',
  mandi: '/mandi',
};

function decodeClaims(token) {
  try {
    const payload = token.split('.')[1];
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    const claims = JSON.parse(json);
    if (claims.exp && claims.exp * 1000 < Date.now()) return null;
    return claims;
  } catch {
    return null;
  }
}

export function middleware(request) {
  const { pathname } = request.nextUrl;

  const guarded = Object.keys(ACCESS).find(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );
  const token = request.cookies.get(TOKEN_COOKIE)?.value;
  const claims = token ? decodeClaims(token) : null;

  // Already signed in → /login bounces to the role's home.
  if (pathname === '/login' && claims) {
    const url = request.nextUrl.clone();
    url.pathname = ROLE_HOME[claims.role] || '/dashboard';
    return NextResponse.redirect(url);
  }

  if (!guarded) return NextResponse.next();

  if (!claims) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    return NextResponse.redirect(url);
  }

  if (!ACCESS[guarded].includes(claims.role)) {
    const url = request.nextUrl.clone();
    url.pathname = ROLE_HOME[claims.role] || '/login';
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/login',
    '/dashboard/:path*',
    '/scenario/:path*',
    '/runs/:path*',
    '/advisor/:path*',
    '/farmer/:path*',
    '/driver/:path*',
    '/mandi/:path*',
  ],
};
