import Head from 'next/head';
import Link from 'next/link';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import PlanViewer from '@/components/PlanViewer/PlanViewer';
import { useRun, useRunTraces, useCachedRunResponse } from '@/hooks/useRuns';
import { useAppContext } from '@/context/AppContext';

/**
 * Runs page — shows the most recent run (the one cached in localStorage
 * by the last scenario submission).  When the backend gains a /api/runs
 * list endpoint we can extend this to a multi-run picker.
 */
export default function RunsPage() {
  const { currentRunId } = useAppContext();
  const cached = useCachedRunResponse();
  const runId = cached?.run_id || currentRunId || null;

  const { data: persistedRun, loading, error } = useRun(runId);
  const { data: traces } = useRunTraces(runId);

  if (!runId) {
    return (
      <>
        <Head>
          <title>Runs | AgentFarm</title>
        </Head>
        <DashboardLayout title="Runs">
          <div
            className="bg-card p-8 text-center font-mono text-muted text-[13px]"
            style={{
              border: '1px solid var(--border)',
              borderRadius: '4px',
            }}
          >
            No runs yet.{' '}
            <Link
              href="/scenario"
              className="text-accent tracking-wider-2 hover:underline"
            >
              RUN A SCENARIO
            </Link>{' '}
            to populate this page.
          </div>
        </DashboardLayout>
      </>
    );
  }

  const runForViewer = cached
    ? {
        runId: cached.run_id,
        kpis: cached.kpis,
        plan: {
          assignments: (cached.plan?.route_plan?.routes || []).map((r, idx) => ({
            truckId: r.truck_id || `route-${idx}`,
            stops: r.stops || [],
            distance_km: r.distance_km,
          })),
        },
      }
    : null;

  return (
    <>
      <Head>
        <title>Runs | AgentFarm</title>
      </Head>
      <DashboardLayout title="Runs" subtitle={`Run ${runId?.slice(0, 8) || '—'}`}>
        <section>
          <div
            className="bg-card mb-6"
            style={{
              border: '1px solid var(--border)',
              borderRadius: '4px',
            }}
          >
            <div
              className="px-5 py-3 flex justify-between items-baseline flex-wrap gap-2"
              style={{ borderBottom: '1px solid var(--border)' }}
            >
              <div>
                <h2
                  className="font-syne font-bold uppercase text-paper tracking-wider-2"
                  style={{ fontSize: '14px' }}
                >
                  ▸ Current Run
                </h2>
                <p
                  className="font-mono text-muted text-[11px] break-all mt-1"
                  style={{ letterSpacing: '0.04em' }}
                >
                  {runId}
                </p>
              </div>
              <Link
                href="/scenario"
                className="font-mono text-accent text-[11px] tracking-wider uppercase hover:underline"
              >
                Run another →
              </Link>
            </div>
            <div className="px-5 py-3 font-mono text-[11.5px] space-y-1">
              {loading && (
                <p className="text-muted">◦ Loading persisted plan from backend…</p>
              )}
              {error && (
                <p style={{ color: 'var(--red-risk)' }}>Backend lookup error: {error}</p>
              )}
              {persistedRun && (
                <p className="text-muted">
                  Persisted at{' '}
                  <span className="text-paper">{persistedRun.created_at}</span>{' '}
                  · validation:{' '}
                  <span
                    style={{
                      color: persistedRun.validation?.valid
                        ? 'var(--green-ok)'
                        : 'var(--red-risk)',
                    }}
                  >
                    {persistedRun.validation?.valid ? 'PASSED' : 'FAILED'}
                  </span>
                </p>
              )}
            </div>
          </div>

          <PlanViewer run={runForViewer} traces={traces} />
        </section>
      </DashboardLayout>
    </>
  );
}
