import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Head from 'next/head';
import { useAppContext } from '@/context/AppContext';

const AGENTS = [
  { tag: '01', title: 'Weather', body: 'Risk classification per farm via OpenWeather' },
  { tag: '02', title: 'Demand', body: '7-day mandi forecasts with festival multipliers' },
  { tag: '03', title: 'Inventory', body: 'Spoilage window tracking & prioritisation' },
  { tag: '04', title: 'Logistics', body: 'OR-Tools capacitated VRP optimisation' },
  { tag: '05', title: 'Validator', body: 'Rule-based feasibility & retry loop' },
  { tag: '06', title: 'Advisor', body: 'Plain-language farmer advice (Kisan Mitra)' },
];

const QUOTES = [
  {
    body:
      'We lose 30–40% of tomatoes between farm and mandi every monsoon. Nobody tells us when to harvest or which market needs supply.',
    who: 'Smallholder Farmer, Belgaum',
  },
  {
    body:
      'I run 10 trucks but dispatch by gut feel. Half the time we reach a mandi that’s already oversupplied while another one nearby is short.',
    who: 'Fleet Operator, Karnataka',
  },
];

/**
 * Landing page — introduces AgentFarm and links into the operator surfaces.
 */
const ROLE_HOME = { fpo: '/dashboard', farmer: '/farmer', mandi: '/mandi' };

export default function HomePage() {
  const [revealed, setRevealed] = useState(false);
  const { user } = useAppContext();
  const loading = false;
  const router = useRouter();

  useEffect(() => setRevealed(true), []);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    if (user.role === 'driver') {
      const runId = typeof window !== 'undefined' ? localStorage.getItem('agentfarm_run_id') : null;
      router.replace(runId ? `/driver/${runId}/${user.entityId}` : '/runs');
    } else {
      router.replace(ROLE_HOME[user.role] || '/login');
    }
  }, [user, loading, router]);

  return (
    <>
      <Head>
        <title>AgentFarm Optimizer</title>
        <meta name="description" content="Agentic AI for sustainable agri supply chains in India" />
      </Head>
      <div className="min-h-screen overflow-hidden" style={{ color: 'var(--text)' }}>
        {/* ambient glow */}
        <div className="fixed inset-0 pointer-events-none z-0">
          <div
            className="absolute top-[-10%] left-[20%] w-[60%] h-[40%]"
            style={{
              background: 'radial-gradient(ellipse, rgba(255,255,255,0.3) 0%, transparent 70%)',
              filter: 'blur(60px)',
            }}
          />
        </div>

        <header className="relative z-10">
          <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
            <span className="text-xl font-bold tracking-tight" style={{ color: 'var(--navy)' }}>
              AgentFarm
            </span>
            <nav className="flex items-center gap-8">
              <Link className="text-sm font-medium hover:text-teal-700 transition-colors" style={{ color: 'var(--text-secondary)' }} href="/dashboard">
                Dashboard
              </Link>
              <Link className="text-sm font-medium hover:text-teal-700 transition-colors" style={{ color: 'var(--text-secondary)' }} href="/scenario">
                Scenario
              </Link>
              <Link className="text-sm font-medium hover:text-teal-700 transition-colors" style={{ color: 'var(--text-secondary)' }} href="/advisor">
                Advisor
              </Link>
            </nav>
          </div>
        </header>

        {/* hero */}
        <section
          className="relative z-10 max-w-5xl mx-auto px-6 pt-24 pb-20 text-center"
          style={{
            opacity: revealed ? 1 : 0,
            transform: revealed ? 'translateY(0)' : 'translateY(24px)',
            transition: 'all 0.8s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          <p className="text-sm font-medium tracking-wide uppercase mb-6" style={{ color: 'var(--accent)' }}>
            Multi-Agent AI for Agriculture
          </p>
          <h1 className="font-serif text-5xl md:text-7xl leading-[1.1] tracking-tight" style={{ color: 'var(--navy)' }}>
            Reducing food waste through<br />
            <span style={{ color: 'var(--accent)' }}>agentic intelligence.</span>
          </h1>
          <p className="mt-8 text-lg md:text-xl max-w-2xl mx-auto leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Six AI agents predict disruptions, optimise truck routes, and advise smallholder farmers —
            cutting perishable waste by up to 35% in under two minutes.
          </p>
          <div className="mt-10 flex justify-center gap-4">
            <Link className="btn-primary" style={{ padding: '14px 32px', fontSize: '15px' }} href="/scenario">
              Run a Scenario
              <Arrow />
            </Link>
            <Link className="btn-secondary" style={{ padding: '14px 32px', fontSize: '15px' }} href="/dashboard">
              Open Dashboard
            </Link>
          </div>
        </section>

        {/* user story */}
        <section className="relative z-10 max-w-5xl mx-auto px-6 py-20">
          <div className="text-center mb-14">
            <h2 className="font-serif text-3xl md:text-4xl tracking-tight" style={{ color: 'var(--navy)' }}>
              User Story:<br />
              <span style={{ color: 'var(--text-secondary)', fontWeight: 400 }}>
                India loses 30–40% of fresh produce every year.
              </span>
            </h2>
          </div>
          <div className="grid md:grid-cols-2 gap-8">
            {QUOTES.map((q) => (
              <div key={q.who} className="text-center px-6">
                <span className="font-serif text-5xl block mb-4" style={{ color: 'var(--navy)', lineHeight: 0.8 }}>
                  “
                </span>
                <p className="text-base leading-relaxed mb-4" style={{ color: 'var(--text-secondary)' }}>
                  {q.body}
                </p>
                <span
                  className="text-sm font-medium px-3 py-1"
                  style={{ color: 'var(--accent)', background: 'linear-gradient(transparent 60%, rgba(94,234,212,0.25) 60%)' }}
                >
                  {q.who}
                </span>
              </div>
            ))}
          </div>
        </section>

        <div className="max-w-5xl mx-auto px-6">
          <div className="h-px" style={{ background: 'var(--border)' }} />
        </div>

        {/* how it works */}
        <section className="relative z-10 max-w-5xl mx-auto px-6 py-20">
          <div className="text-center mb-14">
            <p className="section-label mb-3" style={{ color: 'var(--accent)' }}>
              How It Works
            </p>
            <h2 className="font-serif text-3xl md:text-4xl tracking-tight" style={{ color: 'var(--navy)' }}>
              Six Agents, One Optimised Plan
            </h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 stagger-children">
            {AGENTS.map((a) => (
              <div key={a.tag} className="glass-card p-6 text-center group">
                <div
                  className="w-10 h-10 rounded-full mx-auto mb-3 flex items-center justify-center text-xs font-bold"
                  style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}
                >
                  {a.tag}
                </div>
                <p className="text-sm font-semibold mb-1" style={{ color: 'var(--navy)' }}>
                  {a.title}
                </p>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-tertiary)' }}>
                  {a.body}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* stats */}
        <section className="relative z-10" style={{ background: 'rgba(200,210,220,0.3)' }}>
          <div className="max-w-5xl mx-auto px-6 py-16">
            <div className="grid grid-cols-3 gap-8 text-center">
              <Stat value="20" label="Demo Farms" color="var(--navy)" />
              <Stat value="35%" label="Waste Reduction" color="var(--accent)" />
              <Stat value="<2m" label="Per Scenario" color="var(--navy)" />
            </div>
          </div>
        </section>

        <footer className="relative z-10 border-t" style={{ borderColor: 'var(--border)' }}>
          <div className="max-w-5xl mx-auto px-6 py-8 flex items-center justify-between text-xs" style={{ color: 'var(--text-tertiary)' }}>
            <span>AgentFarm Optimizer · Built for Indian Agriculture</span>
            <span>LangGraph · OR-Tools · FastAPI</span>
          </div>
        </footer>
      </div>
    </>
  );
}

function Stat({ value, label, color }) {
  return (
    <div>
      <p className="font-serif text-4xl font-bold" style={{ color }}>
        {value}
      </p>
      <p className="text-sm mt-1" style={{ color: 'var(--text-tertiary)' }}>
        {label}
      </p>
    </div>
  );
}

function Arrow() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  );
}
