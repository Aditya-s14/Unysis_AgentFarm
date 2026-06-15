import Link from 'next/link';
import { useRouter } from 'next/router';
import { useMemo, useState } from 'react';
import DarkModeToggle from '@/components/Theme/DarkModeToggle';
import { useAppContext } from '@/context/AppContext';
import { useTheme } from '@/context/ThemeContext';
import { getRoleColors } from '@/utils/roleColors';

const ROLE_LABELS = { fpo: 'FPO Admin', farmer: 'Farmer', driver: 'Driver', mandi: 'Mandi Operator' };

export default function DashboardLayout({ children, title, subtitle }) {
  const router = useRouter();
  const { user, logout } = useAppContext();
  const { isDark } = useTheme();
  const [collapsed, setCollapsed] = useState(false);

  const handleSignOut = () => {
    logout();
    router.push('/login');
  };

  const ALL_NAV = [
    { href: '/',          label: 'Home',      icon: HomeIcon,     roles: ['fpo'] },
    { href: '/dashboard', label: 'Dashboard', icon: GridIcon,     roles: ['fpo'] },
    { href: '/scenario',  label: 'Scenario',  icon: BoltIcon,     roles: ['fpo'] },
    { href: '/runs',      label: 'Runs',      icon: ActivityIcon, roles: ['fpo'] },
    { href: '/driver',    label: 'My Route',  icon: TruckIcon,    roles: ['driver'], matchPrefix: '/driver' },
    { href: '/farmer',    label: 'Farmer',    icon: LeafIcon,     roles: ['fpo', 'farmer'] },
    { href: '/mandi',     label: 'Mandi',     icon: StoreIcon,    roles: ['fpo', 'mandi'] },
    { href: '/advisor',   label: 'Advisor',   icon: ChatIcon,     roles: ['fpo'] },
  ];

  const navItems = user ? ALL_NAV.filter((item) => item.roles.includes(user.role)) : ALL_NAV;
  const width = collapsed ? 'var(--sidebar-collapsed)' : 'var(--sidebar-width)';
  const rc = useMemo(() => getRoleColors(user?.role, isDark), [user?.role, isDark]);
  const homeHref = user?.role === 'driver' ? '/driver' : '/';

  return (
    <div className="flex min-h-screen" style={{ background: 'var(--bg)' }}>
      {/* sidebar */}
      <aside
        className="fixed top-0 left-0 h-screen flex flex-col z-40 transition-all duration-300 ease-in-out"
        style={{
          width,
          background: 'var(--sidebar-bg)',
          borderRight: '1px solid var(--sidebar-border)',
        }}
      >
        {/* logo */}
        <Link
          href={homeHref}
          className="flex items-center gap-3 px-4 shrink-0"
          style={{ height: 64, borderBottom: '1px solid var(--sidebar-border)', textDecoration: 'none' }}
        >
          <div style={{
            width: 34, height: 34, borderRadius: 9, background: 'rgba(255,255,255,0.18)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2.5">
              <path d="M2 22 16 8" />
              <path d="M16 8c0-4.4-3.6-8-8-8C7 3.3 4 8 4 12c0 5.5 4.5 10 10 10 4.4 0 8-3.6 8-8 0-2.2-.9-4.3-2.3-5.8" />
            </svg>
          </div>
          {!collapsed && (
            <div style={{ overflow: 'hidden' }}>
              <p style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: 700, fontSize: 15, color: 'var(--sidebar-text)', lineHeight: 1.2 }}>
                AgentFarm
              </p>
              <p style={{ fontSize: 10, color: 'var(--sidebar-text-muted)', letterSpacing: '0.04em' }}>Optimizer v1.0</p>
            </div>
          )}
        </Link>

        {/* nav */}
        <nav className="flex-1 py-3 overflow-y-auto" style={{ padding: '12px 8px' }}>
          {navItems.map((item) => {
            const active = item.matchPrefix
              ? router.pathname.startsWith(item.matchPrefix)
              : router.pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: collapsed ? '10px' : '9px 12px',
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  borderRadius: 8, marginBottom: 2,
                  borderLeft: active ? '2px solid var(--harvest-gold)' : '2px solid transparent',
                  background: active ? 'var(--sidebar-accent-muted)' : 'transparent',
                  color: active ? 'var(--sidebar-text)' : 'var(--sidebar-text-muted)',
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  fontWeight: active ? 600 : 400,
                  fontSize: 13,
                  textDecoration: 'none',
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={e => { if (!active) { e.currentTarget.style.background = 'var(--sidebar-hover)'; e.currentTarget.style.color = 'var(--sidebar-text)'; } }}
                onMouseLeave={e => { if (!active) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--sidebar-text-muted)'; } }}
              >
                <span style={{ flexShrink: 0, color: active ? 'var(--sidebar-text)' : 'inherit' }}><Icon /></span>
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* user info */}
        {user && (
          <div style={{ padding: '10px 8px', borderTop: '1px solid var(--sidebar-border)' }}>
            {!collapsed && (
              <div style={{
                background: isDark ? 'var(--sidebar-card-bg)' : 'rgba(255,255,255,0.92)',
                border: isDark ? '1px solid var(--sidebar-card-border)' : '1px solid rgba(255,255,255,0.4)',
                borderRadius: 10, padding: '10px 12px', marginBottom: 6,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: 7, flexShrink: 0,
                    background: rc.bg, color: rc.text,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: 700, fontSize: 12, fontFamily: "'IBM Plex Sans', sans-serif",
                  }}>
                    {(user.name || user.phone || '?').charAt(0).toUpperCase()}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <p style={{
                      fontSize: 12, fontWeight: 600,
                      color: isDark ? 'var(--sidebar-text)' : 'var(--navy)',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {user.name || user.phone}
                    </p>
                  </div>
                </div>
                <span style={{
                  display: 'inline-block', fontSize: 10, fontWeight: 600, letterSpacing: '0.08em',
                  textTransform: 'uppercase', padding: '2px 7px', borderRadius: 100,
                  background: rc.bg, color: rc.text,
                  fontFamily: "'IBM Plex Sans', sans-serif",
                }}>
                  {ROLE_LABELS[user.role] || user.role}
                </span>
              </div>
            )}
            <button
              type="button"
              onClick={handleSignOut}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                gap: 6, padding: '8px', borderRadius: 8, border: 'none', background: 'transparent',
                color: 'var(--sidebar-text-faint)', fontSize: 12, cursor: 'pointer',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(231,76,60,0.15)'; e.currentTarget.style.color = '#FFB4AB'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--sidebar-text-faint)'; }}
            >
              <LogoutIcon />
              {!collapsed && <span>Sign Out</span>}
            </button>
          </div>
        )}

        {/* theme + collapse */}
        <div style={{ padding: '8px', borderTop: '1px solid var(--sidebar-border)' }}>
          <DarkModeToggle collapsed={collapsed} variant="sidebar" />
          <button
            type="button"
            onClick={() => setCollapsed((c) => !c)}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              gap: 6, padding: '8px', borderRadius: 8, border: 'none', background: 'transparent',
              color: 'var(--sidebar-text-faint)', fontSize: 12, cursor: 'pointer',
              transition: 'color 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--sidebar-text)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--sidebar-text-faint)'}
          >
            <svg
              width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
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

      {/* main content */}
      <div className="flex-1 min-h-screen transition-all duration-300 ease-in-out" style={{ marginLeft: width }}>

        {/* top header */}
        <header
          className="sticky top-0 z-30 flex items-center justify-between px-8"
          style={{
            height: 64,
            background: 'var(--bg-subtle)',
            borderBottom: '1px solid var(--border)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <h1 style={{
              fontFamily: "'IBM Plex Sans', sans-serif",
              fontSize: 17, fontWeight: 700, color: 'var(--navy)',
            }}>
              {title}
            </h1>
            {subtitle && (
              <>
                <span style={{ width: 1, height: 16, background: 'var(--border)' }} />
                <span style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 500 }}>{subtitle}</span>
              </>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <DarkModeToggle variant="header" />
            {user && (
              <span style={{
                fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 100,
                fontFamily: "'IBM Plex Sans', sans-serif", letterSpacing: '0.06em',
                textTransform: 'uppercase',
                background: rc.bg, color: rc.text,
              }}>
                {user.name}
              </span>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className="dot-live" />
              <span style={{ fontSize: 11, color: 'var(--text-tertiary)', fontWeight: 500 }}>Online</span>
            </div>
          </div>
        </header>

        <main style={{ padding: '24px 32px' }}>{children}</main>
      </div>
    </div>
  );
}

/* ── Icons ──────────────────────────────────────────────────────────────── */
const svgProps = {
  width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
  strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round',
};

function HomeIcon()     { return <svg {...svgProps}><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></svg>; }
function GridIcon()     { return <svg {...svgProps}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="4" rx="1" /><rect x="14" y="11" width="7" height="10" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /></svg>; }
function BoltIcon()     { return <svg {...svgProps}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>; }
function ActivityIcon() { return <svg {...svgProps}><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>; }
function ChatIcon()     { return <svg {...svgProps}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>; }
function LeafIcon()     { return <svg {...svgProps}><path d="M2 22 16 8" /><path d="M16 8c0-4.4-3.6-8-8-8C7 3.3 4 8 4 12c0 5.5 4.5 10 10 10 4.4 0 8-3.6 8-8 0-2.2-.9-4.3-2.3-5.8" /></svg>; }
function StoreIcon()    { return <svg {...svgProps}><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" /><line x1="3" y1="6" x2="21" y2="6" /><path d="M16 10a4 4 0 0 1-8 0" /></svg>; }
function TruckIcon() {
  return (
    <svg {...svgProps}>
      <path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11" />
      <path d="M15 18H9" />
      <path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.03A1 1 0 0 0 17.52 8H14" />
      <circle cx="7" cy="18" r="2" />
      <circle cx="17" cy="18" r="2" />
    </svg>
  );
}
function LogoutIcon()   { return <svg {...svgProps}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>; }
