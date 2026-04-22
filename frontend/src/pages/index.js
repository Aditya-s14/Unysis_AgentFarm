import Link from 'next/link';
import Head from 'next/head';

/**
 * Landing page — introduces AgentFarm and links to the dashboard.
 */
export default function HomePage() {
  return (
    <>
      <Head>
        <title>AgentFarm Optimizer</title>
      </Head>
      <main className="min-h-screen bg-agri-cream">
        <section className="max-w-5xl mx-auto px-6 py-20">
          <p className="uppercase tracking-widest text-sm text-agri-green font-semibold">
            AgentFarm Optimizer
          </p>
          <h1 className="mt-4 text-5xl font-bold text-agri-green-dark leading-tight">
            Agentic AI for sustainable Indian agri supply chains
          </h1>
          <p className="mt-6 text-lg text-gray-700 max-w-2xl">
            A six-agent system that predicts weather disruptions, forecasts demand, tracks
            spoilage risk, optimizes truck routes, validates plans, and advises smallholder
            farmers — all in under two minutes per scenario.
          </p>

          <div className="mt-10 flex flex-wrap gap-4">
            <Link
              href="/dashboard"
              className="px-6 py-3 rounded-md bg-agri-green text-white font-medium hover:bg-agri-green-dark transition"
            >
              Open Dashboard
            </Link>
            <Link
              href="/scenario"
              className="px-6 py-3 rounded-md bg-white border border-agri-green text-agri-green font-medium hover:bg-agri-green-light/30 transition"
            >
              Run a Scenario
            </Link>
            <Link
              href="/advisor"
              className="px-6 py-3 rounded-md bg-agri-orange text-white font-medium hover:bg-agri-orange-light transition"
            >
              Ask the Advisor
            </Link>
          </div>

          <div className="mt-16 grid md:grid-cols-3 gap-6">
            <FeatureCard
              title="Monsoon &amp; Heat Wave"
              body="Pre-built disruption scenarios for the Indian growing calendar."
            />
            <FeatureCard
              title="20 farms, 10 mandis"
              body="Optimizes pickups, cold storage, and last-mile routing across Karnataka and Maharashtra."
            />
            <FeatureCard
              title="Learns from outcomes"
              body="Past deliveries feed back into tomorrow's plan via the Outcome Store."
            />
          </div>
        </section>
      </main>
    </>
  );
}

/** Small marketing card used on the landing page. */
function FeatureCard({ title, body }) {
  return (
    <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-100">
      <h3 className="font-semibold text-agri-green-dark">{title}</h3>
      <p className="mt-2 text-sm text-gray-600">{body}</p>
    </div>
  );
}
