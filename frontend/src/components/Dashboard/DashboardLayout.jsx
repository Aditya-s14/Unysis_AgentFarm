import Link from 'next/link';
import { useRouter } from 'next/router';
import { useState } from 'react';
import { useAppContext } from '@/context/AppContext';

const ROLE_LABELS = { fpo: 'FPO Admin', farmer: 'Farmer', driver: 'Driver', mandi: 'Mandi Operator' };
const ROLE_COLORS = {
  fpo:    { bg: '#1e3a5f', text: '#fff' },
  farmer: { bg: '#166534', text: '#fff' },
  driver: { bg: '#92400e', text: '#fff' },
  mandi:  { bg: '#581c87', text: '#fff' },
};

export default function DashboardLayout({ children, title, subtitle }) {
  const router = useRouter();
  const { user, logout } = useAppContext();
  const [collapsed, setCollapsed] = useState(false);

  const handleSignOut = () => {
    logout();
    router.push('/login');
  };

  const ALL_NAV = [
    { href: '/',          label: 'Home',      icon: HomeIcon,     roles: ['fpo'] },
    { href: '/dashboard', label: 'Dashboard', icon: GridIcon,     roles: ['fpo'] },
    { href: '/scenario',  label: 'Scenario',  icon: BoltIcon,     roles: ['fpo'] },
    { href: '/runs',      label: 'Runs',      icon: ActivityIcon, roles: ['fpo', 'driver'] },
    { href: '/farmer',    label: 'Farmer',    icon: LeafIcon,     roles: ['fpo', 'farmer'] },
    { href: '/mandi',     label: 'Mandi',     icon: StoreIcon,    roles: ['fpo', 'mandi'] },
    { href: '/advisor',   label: 'Advisor',   icon: ChatIcon,     roles: ['fpo'] },
  ];

  const navItems = user
    ? ALL_NAV.filter((item) => item.roles.includes(user.role))
    : ALL_NAV;

  const width = collapsed ? 'var(--sidebar-collapsed)' : 'var(--sidebar-width)';

  return (
    <div className="flex min-h-screen">
      <aside
        className="fixed top-0 left-0 h-screen flex flex-col z-40 transition-all duration-300 ease-in-out"
        style={{
          width,
          background: 'rgba(225,231,238,0.5)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          borderRight: '1px solid rgba(255,255,255,0.3)',
        }}
      >
        {/* logo */}
        <Link
          href="/"
          className="flex items-center gap-3 px-5 h-16 shrink-0 border-b"
          style={{ borderColor: 'rgba(255,255,255,0.25)' }}
        >
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: 'var(--navy)', color: '#fff' }}
          >
            <span className="text-xs font-bold">AF</span>
          </div>
          {!collapsed && (
            <div>
              <p className="text-sm font-bold tracking-tight" style={{ color: 'var(--navy)' }}>
                AgentFarm
              </p>
              <p className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                Optimizer v1.0
              </p>
            </div>
          )}
        </Link>

        {/* nav */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const active = router.pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${
                  collapsed ? 'justify-center' : ''
                }`}
                style={{
                  color: active ? 'var(--navy)' : 'var(--text-tertiary)',
                  background: active ? 'var(--bg-elevated)' : 'transparent',
                  fontWeight: active ? 600 : 400,
                  fontSize: '13px',
                }}
              >
                <span className="flex-shrink-0">
                  <Icon />
                </span>
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* user pill + sign out */}
        {user && (
          <div className="px-3 py-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.25)' }}>
            {!collapsed && (
              <div className="mb-2 px-2 py-2 rounded-lg" style={{ background: 'rgba(255,255,255,0.25)' }}>
                <div className="flex items-center gap-2 mb-1">
                  <div
                    className="w-6 h-6 rounded flex items-center justify-center text-xs font-bold flex-shrink-0"
                    style={{ background: ROLE_COLORS[user.role]?.bg || '#1e3a5f', color: '#fff' }}
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
                  style={{ background: ROLE_COLORS[user.role]?.bg || '#1e3a5f', color: '#fff' }}
                >
                  {ROLE_LABELS[user.role] || user.role}
                </span>
              </div>
            )}
            <button
              type="button"
              onClick={handleSignOut}
              className="w-full flex items-center justify-center gap-2 py-2 rounded-lg transition-all"
              style={{ color: 'var(--text-tertiary)', background: 'transparent', border: 'none', fontSize: '12px', cursor: 'pointer' }}
            >
              <LogoutIcon />
              {!collapsed && <span>Sign Out</span>}
            </button>
          </div>
        )}

        {/* collapse toggle */}
        <div className="px-3 py-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.25)' }}>
          <button
            type="button"
            onClick={() => setCollapsed((c) => !c)}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg transition-all"
            style={{ color: 'var(--text-tertiary)', background: 'transparent', border: 'none', fontSize: '12px' }}
          >
            <svg
              width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
              style={{ transition: 'transform 0.3s ease', transform: collapsed ? 'rotate(180deg)' : 'rotate(0deg)' }}
            >
              <polyline points="11 17 6 12 11 7" />
              <polyline points="18 17 13 12 18 7" />
            </svg>
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </aside>

      {/* content */}
      <div
        className="flex-1 min-h-screen transition-all duration-300 ease-in-out"
        style={{ marginLeft: width }}
      >
        <header
          className="sticky top-0 z-30 px-8 h-16 flex items-center justify-between border-b"
          style={{
            borderColor: 'rgba(255,255,255,0.3)',
            background: 'rgba(213,221,229,0.6)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
          }}
        >
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-bold tracking-tight" style={{ color: 'var(--navy)' }}>
              {title}
            </h1>
            {subtitle && (
              <>
                <span className="w-px h-4" style={{ background: 'var(--border)' }} />
                <span className="text-xs font-medium" style={{ color: 'var(--text-tertiary)' }}>
                  {subtitle}
                </span>
              </>
            )}
          </div>
          <div className="flex items-center gap-3">
            {user && (
              <span
                className="text-xs font-semibold px-2 py-0.5 rounded"
                style={{ background: ROLE_COLORS[user.role]?.bg || '#1e3a5f', color: '#fff' }}
              >
                {user.name}
              </span>
            )}
            <span className="dot-live" />
            <span className="text-xs font-medium" style={{ color: 'var(--text-tertiary)' }}>
              Online
            </span>
          </div>
        </header>

        <main className="px-8 py-6">{children}</main>
      </div>
    </div>
  );
}

/* ── Sidebar icons (recovered from the lost build) ──────────────────────── */
const svgProps = {
  width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
  strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round',
};

function HomeIcon() {
  return (
    <svg {...svgProps}>
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  );
}
function GridIcon() {
  return (
    <svg {...svgProps}>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="4" rx="1" />
      <rect x="14" y="11" width="7" height="10" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
    </svg>
  );
}
function BoltIcon() {
  return (
    <svg {...svgProps}>
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}
function ActivityIcon() {
  return (
    <svg {...svgProps}>
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}
function ChatIcon() {
  return (
    <svg {...svgProps}>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
function LeafIcon() {
  return (
    <svg {...svgProps}>
      <path d="M2 22 16 8" />
      <path d="M16 8c0-4.4-3.6-8-8-8C7 3.3 4 8 4 12c0 5.5 4.5 10 10 10 4.4 0 8-3.6 8-8 0-2.2-.9-4.3-2.3-5.8" />
    </svg>
  );
}
function StoreIcon() {
  return (
    <svg {...svgProps}>
      <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
      <line x1="3" y1="6" x2="21" y2="6" />
      <path d="M16 10a4 4 0 0 1-8 0" />
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
