import Link from 'next/link';
import { useRouter } from 'next/router';
import { useMemo } from 'react';
import { useAppContext } from '@/context/AppContext';
import { useTheme } from '@/context/ThemeContext';
import { getRoleColors } from '@/utils/roleColors';

const SIDEBAR_WIDTH = 'var(--sidebar-width)';

const ROLE_LABELS = { driver: 'Driver' };

const svgProps = {
  width: 20,
  height: 20,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

function HomeIcon() {
  return (
    <svg {...svgProps}>
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  );
}

function LogoutIcon() {
  return (
    <svg {...svgProps}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

/**
 * Driver sidebar — matches DashboardLayout styling with truck context + sign out.
 */
export default function DriverSidebar({ truckLabel = null, routeHref = null }) {
  const router = useRouter();
  const { user, logout } = useAppContext();
  const { isDark } = useTheme();
  const rc = useMemo(() => getRoleColors(user?.role, isDark), [user?.role, isDark]);

  const handleSignOut = () => {
    logout();
    router.push('/login');
  };

  const routeActive = routeHref && router.asPath === routeHref;

  return (
    <aside
      className="fixed top-0 left-0 h-screen flex flex-col z-40"
      style={{
        width: SIDEBAR_WIDTH,
        background: 'rgba(225,231,238,0.5)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        borderRight: '1px solid rgba(255,255,255,0.3)',
      }}
    >
      <Link
        href="/driver"
        className="flex items-center gap-3 px-5 h-16 shrink-0 border-b"
        style={{ borderColor: 'rgba(255,255,255,0.25)', textDecoration: 'none' }}
      >
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: 'var(--navy)', color: '#fff' }}
        >
          <span className="text-xs font-bold">AF</span>
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight" style={{ color: 'var(--navy)' }}>
            AgentFarm
          </p>
          <p className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
            Driver
          </p>
        </div>
      </Link>

      {truckLabel && (
        <div
          className="px-5 py-4 border-b shrink-0"
          style={{ borderColor: 'rgba(255,255,255,0.25)' }}
        >
          <p
            className="font-syne font-bold uppercase tracking-tight"
            style={{ color: 'var(--navy)', fontSize: '16px' }}
          >
            {truckLabel}
          </p>
          <span
            className="font-mono uppercase tracking-wider mt-2 inline-block px-2 py-1 rounded"
            style={{
              fontSize: '10px',
              color: '#22A06B',
              background: 'rgba(76, 175, 80, 0.12)',
              border: '1px solid rgba(76, 175, 80, 0.35)',
            }}
          >
            ON ROUTE
          </span>
        </div>
      )}

      <nav className="flex-1 py-4 px-3 space-y-1">
        {routeHref && (
          <Link
            href={routeHref}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200"
            style={{
              color: routeActive ? 'var(--navy)' : 'var(--text-tertiary)',
              background: routeActive ? 'var(--bg-elevated)' : 'transparent',
              fontWeight: routeActive ? 600 : 400,
              fontSize: '13px',
              textDecoration: 'none',
            }}
          >
            <span className="flex-shrink-0">
              <HomeIcon />
            </span>
            <span>My Route</span>
          </Link>
        )}
      </nav>

      {user && (
        <div className="px-3 py-3 border-t shrink-0" style={{ borderColor: 'rgba(255,255,255,0.25)' }}>
          <div className="mb-2 px-2 py-2 rounded-lg" style={{ background: 'rgba(255,255,255,0.25)' }}>
            <div className="flex items-center gap-2 mb-1">
              <div
                className="w-6 h-6 rounded flex items-center justify-center text-xs font-bold flex-shrink-0"
                style={{ background: rc.bg, color: rc.text }}
              >
                {(user.name || user.phone || '?').charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold truncate" style={{ color: 'var(--navy)' }}>
                  {user.name || user.phone}
                </p>
              </div>
            </div>
            <span
              className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded"
              style={{ background: rc.bg, color: rc.text }}
            >
              {ROLE_LABELS.driver}
            </span>
          </div>
          <button
            type="button"
            onClick={handleSignOut}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg transition-all"
            style={{
              color: 'var(--text-tertiary)',
              background: 'transparent',
              border: 'none',
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            <LogoutIcon />
            <span>Sign Out</span>
          </button>
        </div>
      )}
    </aside>
  );
}

export { SIDEBAR_WIDTH };
