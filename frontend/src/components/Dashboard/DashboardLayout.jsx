import Link from 'next/link';
import { useRouter } from 'next/router';

/**
 * Shared chrome for logged-in pages: top nav + content slot.
 * Keeps the same look across Dashboard, Scenario, Runs, and Advisor.
 */
export default function DashboardLayout({ children, title }) {
  const router = useRouter();

  const navItems = [
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/scenario', label: 'Scenario' },
    { href: '/runs', label: 'Runs' },
    { href: '/advisor', label: 'Advisor' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="bg-agri-green-dark text-white">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="font-bold text-lg tracking-tight">
            AgentFarm
          </Link>
          <nav className="flex gap-1">
            {navItems.map((item) => {
              const active = router.pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3 py-2 rounded-md text-sm transition ${
                    active
                      ? 'bg-white/20 text-white'
                      : 'text-white/80 hover:bg-white/10'
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
          <h1 className="text-2xl font-bold text-agri-green-dark mb-6">{title}</h1>
        )}
        {children}
      </main>
    </div>
  );
}
