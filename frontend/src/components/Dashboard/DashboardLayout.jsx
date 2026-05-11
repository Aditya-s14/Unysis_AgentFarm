import Link from 'next/link';
import { useRouter } from 'next/router';

/**
 * DashboardLayout — mission-control chrome shared by every authed page.
 * Top bar: blinking "live" dot · AGENTFARM logotype · status meta · nav.
 */
export default function DashboardLayout({ children, title, subtitle }) {
  const router = useRouter();

  const navItems = [
    { href: '/dashboard', label: 'DASHBOARD' },
    { href: '/scenario',  label: 'SCENARIO'  },
    { href: '/runs',      label: 'RUNS'      },
    { href: '/advisor',   label: 'ADVISOR'   },
  ];

  return (
    <div className="min-h-screen bg-canvas text-paper">
      <header className="border-b border-accent/80" style={{ borderColor: 'var(--accent)' }}>
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between flex-wrap gap-4">
          <Link href="/" className="flex items-center gap-3 group">
            <span
              className="inline-block w-2 h-2 rounded-full bg-ok"
              style={{ animation: 'blink 2s infinite' }}
              aria-hidden
            />
            <span className="font-syne font-extrabold text-accent tracking-wider-2 text-xl">
              AGENTFARM
            </span>
            <span className="hidden sm:inline text-[10px] text-muted tracking-wider-2">
              · OPTIMIZER v0.1
            </span>
          </Link>
          <nav className="flex items-center gap-1 text-[11px]">
            {navItems.map((item) => {
              const active = router.pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3 py-2 tracking-wider-2 transition ${
                    active
                      ? 'text-accent'
                      : 'text-muted hover:text-accent'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {title && (
          <div className="mb-6 flex items-baseline justify-between flex-wrap gap-2">
            <h1 className="font-syne font-bold text-paper text-3xl tracking-wider-2 uppercase">
              {title}
            </h1>
            {subtitle && (
              <span className="text-[11px] text-muted tracking-wider-2 uppercase">
                {subtitle}
              </span>
            )}
          </div>
        )}
        {children}
      </main>
    </div>
  );
}
