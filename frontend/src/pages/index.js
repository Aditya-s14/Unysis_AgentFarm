import Link from 'next/link';
import Head from 'next/head';

/**
 * Landing page — introduces AgentFarm and links into the operator surfaces.
 */
export default function HomePage() {
  return (
    <>
      <Head>
        <title>AgentFarm Optimizer</title>
      </Head>
      <main className="min-h-screen bg-canvas text-paper">
        <header
          className="border-b"
          style={{ borderColor: 'var(--accent)' }}
        >
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-3">
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
          </div>
        </header>

        <section className="max-w-6xl mx-auto px-6 py-16">
          <p
            className="font-mono uppercase mb-4"
            style={{
              color: 'var(--accent)',
              fontSize: '0.7rem',
              letterSpacing: '0.2em',
            }}
          >
            ▸ Mission Control for Indian Agri Supply Chains
          </p>
          <h1 className="font-syne font-extrabold text-paper text-5xl md:text-6xl leading-[1.05] tracking-wider-2 uppercase">
            Agentic AI for<br />sustainable<br /><span className="text-accent">agri logistics.</span>
          </h1>
          <p className="mt-6 font-mono text-muted text-base max-w-2xl leading-relaxed">
            A six-agent system that predicts weather disruptions, forecasts demand, tracks
            spoilage risk, optimises truck routes, validates plans, and advises smallholder
            farmers — all in under two minutes per scenario.
          </p>

          <div className="mt-10 flex flex-wrap gap-3">
            <PrimaryLink href="/scenario">RUN A SCENARIO →</PrimaryLink>
            <SecondaryLink href="/dashboard">OPEN DASHBOARD</SecondaryLink>
            <SecondaryLink href="/advisor">ASK THE ADVISOR</SecondaryLink>
          </div>

          <div className="mt-20 grid md:grid-cols-3 gap-4">
            <FeatureCard
              tag="01"
              title="Monsoon & Heat Wave"
              body="Pre-built disruption scenarios for the Indian growing calendar."
            />
            <FeatureCard
              tag="02"
              title="20 farms · 10 mandis"
              body="Optimises pickups, cold storage, and last-mile routing across Karnataka and Maharashtra."
            />
            <FeatureCard
              tag="03"
              title="Learns from outcomes"
              body="Past deliveries feed back into tomorrow's plan via the Outcome Store."
            />
          </div>
        </section>
      </main>
    </>
  );
}

function PrimaryLink({ href, children }) {
  return (
    <Link
      href={href}
      className="px-5 py-3 font-mono tracking-wider-2 transition"
      style={{
        background: 'var(--accent)',
        color: '#0D1F0F',
        fontSize: '12px',
        fontWeight: 600,
        borderRadius: '2px',
        letterSpacing: '0.15em',
      }}
    >
      {children}
    </Link>
  );
}

function SecondaryLink({ href, children }) {
  return (
    <Link
      href={href}
      className="px-5 py-3 font-mono tracking-wider-2 transition hover:text-accent hover:border-accent"
      style={{
        color: 'var(--muted)',
        border: '1px solid var(--border)',
        fontSize: '12px',
        borderRadius: '2px',
        letterSpacing: '0.15em',
      }}
    >
      {children}
    </Link>
  );
}

function FeatureCard({ tag, title, body }) {
  return (
    <div
      className="p-5 bg-card"
      style={{
        border: '1px solid var(--border)',
        borderTop: '3px solid var(--accent)',
        borderRadius: '4px',
      }}
    >
      <p
        className="font-mono uppercase mb-3"
        style={{
          color: 'var(--accent)',
          fontSize: '0.65rem',
          letterSpacing: '0.2em',
        }}
      >
        {tag}
      </p>
      <h3
        className="font-syne font-bold text-paper uppercase tracking-wider"
        style={{ fontSize: '15px' }}
      >
        {title}
      </h3>
      <p className="mt-3 font-mono text-muted text-[12px] leading-relaxed">{body}</p>
    </div>
  );
}
