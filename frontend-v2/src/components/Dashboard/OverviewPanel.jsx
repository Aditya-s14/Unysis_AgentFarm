import { DEMO_FARMS, DEMO_DEMAND_POINTS, DEMO_TRUCKS } from '@/utils/demoFixtures';

/**
 * OverviewPanel — descriptive banner used at the top of the dashboard.
 * Shows system status and a short summary of the most recent run.
 * Counts are driven by the actual demo fixtures (20 / 10 / 10).
 */
export default function OverviewPanel({ lastRun }) {
  const totalCapacity = DEMO_TRUCKS.reduce((s, t) => s + t.capacity_kg, 0);

  return (
    <div
      className="bg-card p-5 mb-6"
      style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
    >
      <div className="flex flex-wrap justify-between gap-6">
        <div>
          <p
            className="font-mono uppercase mb-2"
            style={{ color: 'var(--accent)', fontSize: '0.65rem', letterSpacing: '0.15em' }}
          >
            ▸ System Overview
          </p>
          <p className="font-mono text-paper text-[13px] leading-relaxed">
            Six autonomous agents currently monitoring{' '}
            <span className="text-accent">{DEMO_FARMS.length}</span> farms,{' '}
            <span className="text-accent">{DEMO_DEMAND_POINTS.length}</span> mandis, and{' '}
            <span className="text-accent">{DEMO_TRUCKS.length}</span> trucks{' '}
            <span className="text-muted">({(totalCapacity / 1000).toFixed(0)}t total capacity).</span>
          </p>
        </div>
        <div className="text-right">
          <p
            className="font-mono uppercase text-muted mb-1"
            style={{ fontSize: '0.65rem', letterSpacing: '0.15em' }}
          >
            ▸ Last Run
          </p>
          <p
            className="font-syne font-bold text-paper"
            style={{ fontSize: '13px', letterSpacing: '0.05em' }}
          >
            {lastRun?.runId || 'No runs yet'}
          </p>
          <p className="font-mono text-muted text-[11px] mt-1">
            {lastRun?.createdAt || 'Run a scenario to populate'}
          </p>
        </div>
      </div>
    </div>
  );
}
