import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Head from 'next/head';
import DarkModeToggle from '@/components/Theme/DarkModeToggle';
import { useAppContext } from '@/context/AppContext';

const AGENT_COLORS = ['var(--accent)', 'var(--blue-mandi)', 'var(--orange-dmd)', 'var(--purple-log)', 'var(--cyan-info)', 'var(--green-ok)'];

const AGENTS = [
  { tag: '01', title: 'Weather',   body: 'Risk classification per farm via OpenWeather', color: 'var(--blue-mandi)' },
  { tag: '02', title: 'Demand',    body: '7-day mandi forecasts with festival multipliers', color: 'var(--orange-dmd)' },
  { tag: '03', title: 'Logistics', body: 'OR-Tools capacitated VRP optimisation', color: 'var(--purple-log)' },
  { tag: '04', title: 'Validator', body: 'Rule-based feasibility & retry loop', color: 'var(--cyan-info)' },
  { tag: '05', title: 'Advisor',   body: 'Plain-language farmer advice (Kisan Mitra)', color: 'var(--accent)' },
];

const ROLE_HOME = { fpo: '/dashboard', farmer: '/farmer', mandi: '/mandi' };

export default function HomePage() {
  const [revealed, setRevealed] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const { user } = useAppContext();
  const router = useRouter();

  useEffect(() => {
    const t = setTimeout(() => { setRevealed(true); setHydrated(true); }, 80);
    return () => clearTimeout(t);
  }, []);

  // Only redirect already-authenticated users — logged-out visitors see the landing page.
  useEffect(() => {
    if (!hydrated || !user) return;
    if (user.role === 'driver') {
      const runId = typeof window !== 'undefined' ? localStorage.getItem('agentfarm_run_id') : null;
      router.replace(runId ? `/driver/${runId}/${user.entityId}` : '/driver');
    } else {
      router.replace(ROLE_HOME[user.role] || '/dashboard');
    }
  }, [hydrated, user, router]);

  return (
    <>
      <Head>
        <title>AgentFarm Optimizer</title>
        <meta name="description" content="Agentic AI for sustainable agri supply chains in India" />
      </Head>

      <div className="min-h-screen overflow-hidden relative" style={{ background: 'var(--bg)', color: 'var(--text)' }}>
        <div style={{ position: 'fixed', top: 16, right: 16, zIndex: 50 }}>
          <DarkModeToggle variant="header" />
        </div>

        {/* ambient mesh glows */}
        <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
          <div style={{
            position: 'absolute', top: '-15%', left: '10%',
            width: '50%', height: '50%',
            background: 'radial-gradient(ellipse, rgba(34,160,107,0.10) 0%, transparent 70%)',
            filter: 'blur(80px)',
            animation: 'mesh-move 20s ease-in-out infinite',
          }} />
          <div style={{
            position: 'absolute', bottom: '-10%', right: '5%',
            width: '40%', height: '40%',
            background: 'radial-gradient(ellipse, rgba(74,144,226,0.08) 0%, transparent 70%)',
            filter: 'blur(80px)',
            animation: 'mesh-move 25s ease-in-out infinite reverse',
          }} />
        </div>

        {/* header */}
        <header className="relative z-10" style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div style={{
                width: 32, height: 32, borderRadius: 8, background: 'var(--accent)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2.5">
                  <path d="M2 22 16 8" /><path d="M16 8c0-4.4-3.6-8-8-8C7 3.3 4 8 4 12c0 5.5 4.5 10 10 10 4.4 0 8-3.6 8-8 0-2.2-.9-4.3-2.3-5.8" />
                </svg>
              </div>
              <span style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: 700, fontSize: 18, color: 'var(--navy)' }}>
                AgentFarm
              </span>
            </div>
            <nav className="flex items-center gap-5">
              {hydrated && user ? (
                <>
                  {[['Dashboard', '/dashboard'], ['Scenario', '/scenario'], ['Advisor', '/advisor']].map(([label, href]) => (
                    <Link key={href} href={href} style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', transition: 'color 0.15s' }}
                      onMouseEnter={e => e.target.style.color = 'var(--accent)'}
                      onMouseLeave={e => e.target.style.color = 'var(--text-secondary)'}
                    >
                      {label}
                    </Link>
                  ))}
                </>
              ) : (
                <Link href="/login" className="btn-primary" style={{ padding: '8px 20px', fontSize: 13, borderRadius: 8 }}>
                  Sign In
                </Link>
              )}
            </nav>
          </div>
        </header>

        {/* hero */}
        <section
          className="relative z-10 max-w-5xl mx-auto px-6 pt-28 pb-24 text-center"
          style={{
            opacity: revealed ? 1 : 0,
            transform: revealed ? 'translateY(0)' : 'translateY(28px)',
            transition: 'opacity 0.8s cubic-bezier(0.16,1,0.3,1), transform 0.8s cubic-bezier(0.16,1,0.3,1)',
          }}
        >
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 24,
            padding: '4px 14px', borderRadius: 100,
            border: '1px solid rgba(34,160,107,0.30)',
            background: 'rgba(34,160,107,0.10)',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)', display: 'inline-block' }} />
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)', fontFamily: "'IBM Plex Sans', sans-serif", letterSpacing: '0.08em' }}>
              MULTI-AGENT AI FOR AGRICULTURE
            </span>
          </div>

          <h1 style={{
            fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: 700,
            fontSize: 'clamp(36px, 6vw, 68px)', lineHeight: 1.1,
            color: 'var(--navy)', letterSpacing: '-0.02em', marginBottom: 24,
          }}>
            Reducing food waste<br />
            through{' '}
            <span style={{ color: 'var(--accent)' }}>agentic intelligence.</span>
          </h1>

          <p style={{ fontSize: 18, color: 'var(--text-secondary)', maxWidth: 560, margin: '0 auto 40px', lineHeight: 1.7 }}>
            Five AI agents predict disruptions, optimise truck routes, and advise smallholder farmers.
          </p>

          <div style={{ display: 'flex', justifyContent: 'center', gap: 12 }}>
            <Link href="/scenario" className="btn-primary" style={{ padding: '12px 28px', fontSize: 15, borderRadius: 10 }}>
              Run a Scenario
              <ArrowIcon />
            </Link>
            <Link href="/dashboard" className="btn-secondary" style={{ padding: '12px 28px', fontSize: 15, borderRadius: 10 }}>
              Open Dashboard
            </Link>
          </div>
        </section>

        {/* how it works */}
        <section className="relative z-10 max-w-5xl mx-auto px-6 pb-24">
          <div className="text-center" style={{ marginBottom: 48 }}>
            <p className="section-label" style={{ color: 'var(--accent)', marginBottom: 12 }}>How It Works</p>
            <h2 style={{
              fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: 700,
              fontSize: 'clamp(24px, 4vw, 40px)', color: 'var(--navy)', lineHeight: 1.2,
            }}>
              Five Agents, One Optimised Plan
            </h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 stagger-children">
            {AGENTS.map((a) => (
              <div key={a.tag} style={{
                background: 'var(--bg-card)', border: '1px solid var(--border)',
                borderTop: `3px solid ${a.color}`,
                borderRadius: 12, padding: '22px 20px',
                transition: 'border-color 0.2s, box-shadow 0.2s',
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = a.color; e.currentTarget.style.boxShadow = `0 8px 24px rgba(0,0,0,0.3)`; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none'; }}
              >
                <div style={{
                  width: 32, height: 32, borderRadius: 8, marginBottom: 14,
                  background: `rgba(${a.color === 'var(--accent)' ? '34,197,94' : a.color === 'var(--blue-mandi)' ? '96,165,250' : a.color === 'var(--orange-dmd)' ? '251,146,60' : a.color === 'var(--red-risk)' ? '248,113,113' : a.color === 'var(--purple-log)' ? '192,132,252' : '103,232,249'},0.12)`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <span style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 11, fontWeight: 600, color: a.color }}>{a.tag}</span>
                </div>
                <p style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: 600, fontSize: 14, color: 'var(--navy)', marginBottom: 6 }}>{a.title}</p>
                <p style={{ fontSize: 12, lineHeight: 1.6, color: 'var(--text-tertiary)' }}>{a.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* cta strip */}
        <div className="relative z-10" style={{ background: 'var(--bg-subtle)', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
          <div className="max-w-5xl mx-auto px-6 py-16 flex flex-col md:flex-row items-center justify-between gap-8">
            <div>
              <h3 style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: 700, fontSize: 26, color: 'var(--navy)' }}>
                Ready to optimise your supply chain?
              </h3>
            </div>
            <Link href="/scenario" className="btn-primary" style={{ padding: '14px 32px', fontSize: 15, whiteSpace: 'nowrap' }}>
              Get Started <ArrowIcon />
            </Link>
          </div>
        </div>

        {/* footer */}
        <footer style={{ borderTop: '1px solid var(--border)' }}>
          <div className="max-w-5xl mx-auto px-6 py-8 flex items-center justify-between">
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>AgentFarm Optimizer · Built for Indian Agriculture</span>
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>LangGraph · OR-Tools · FastAPI</span>
          </div>
        </footer>
      </div>
    </>
  );
}

function ArrowIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
    </svg>
  );
}
