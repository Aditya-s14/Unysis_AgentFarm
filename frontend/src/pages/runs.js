import Head from 'next/head';
import Link from 'next/link';
import { useState } from 'react';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import PlanViewer from '@/components/PlanViewer/PlanViewer';
import { useRun, useCachedRunResponse } from '@/hooks/useRuns';
import { useAppContext } from '@/context/AppContext';
import { approveRun } from '@/api/client';

/**
 * Runs page — shows the most recent run (the one cached in localStorage
 * by the last scenario submission).  When the backend gains a /api/runs
 * list endpoint we can extend this to a multi-run picker.
 */
export default function RunsPage() {
  const { currentRunId, user } = useAppContext();
  const cached = useCachedRunResponse();
  const runId = cached?.run_id || currentRunId || null;

  const { data: persistedRun, loading, error } = useRun(runId);
  const alreadyApproved = persistedRun?.approval_status === 'dispatched' || persistedRun?.approved_at;
  const [approveStatus, setApproveStatus] = useState('idle'); // idle | loading | done | error

  async function handleApprove() {
    if (!runId) return;
    setApproveStatus('loading');
    try {
      await approveRun(runId);
      setApproveStatus('done');
    } catch (err) {
      // 409 = already approved — treat as success
      if (err?.response?.status === 409) {
        setApproveStatus('done');
      } else {
        setApproveStatus('error');
      }
    }
  }

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
          assignments: (cached.plan?.route_plan?.routes || []).map((r, idx) => {
            const stops = r.stops || [];
            const totalKg = stops.reduce((sum, s) => sum + (s.load_kg || 0), 0);
            return {
              truckId: r.truck_id || `route-${idx}`,
              stops,
              distance_km: r.distance_km ? Number(r.distance_km).toFixed(1) : null,
              loadKg: totalKg || null,
              duration_minutes: r.duration_minutes,
            };
          }),
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
              <div className="flex items-center gap-3">
                {user?.role === 'fpo' && (
                  (approveStatus === 'done' || alreadyApproved) ? (
                    <span className="font-mono text-[11px]" style={{ color: 'var(--green-ok)' }}>
                      &#10003; Plan approved
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={handleApprove}
                      disabled={approveStatus === 'loading'}
                      className="font-mono uppercase tracking-wider px-4 py-1.5 text-[11px]"
                      style={{
                        background: approveStatus === 'error' ? 'rgba(220,50,50,0.1)' : 'rgba(76,175,80,0.1)',
                        border: `1px solid ${approveStatus === 'error' ? 'var(--red-risk)' : 'var(--green-ok)'}`,
                        color: approveStatus === 'error' ? 'var(--red-risk)' : 'var(--green-ok)',
                        borderRadius: '4px',
                        cursor: approveStatus === 'loading' ? 'not-allowed' : 'pointer',
                        opacity: approveStatus === 'loading' ? 0.6 : 1,
                      }}
                    >
                      {approveStatus === 'loading' ? 'Approving…' : approveStatus === 'error' ? 'Retry Approve' : 'Approve Plan'}
                    </button>
                  )
                )}
                <Link
                  href="/scenario"
                  className="font-mono text-accent text-[11px] tracking-wider uppercase hover:underline"
                >
                  Run another →
                </Link>
              </div>
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
                  <span className="text-paper">
                    {persistedRun.created_at
                      ? new Date(persistedRun.created_at).toLocaleString()
                      : '—'}
                  </span>{' '}
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

          {/* Driver CTA — jump straight to their truck dashboard */}
          {user?.role === 'driver' && runId && (
            <div
              className="mt-4 p-4 text-center"
              style={{ border: '1px solid var(--accent)', borderRadius: '4px', background: 'rgba(94,234,212,0.06)' }}
            >
              <p className="font-mono text-[11px] mb-3" style={{ color: 'var(--muted)' }}>
                A route has been assigned to your truck.
              </p>
              <Link
                href={`/driver/${runId}/${user.entityId}`}
                className="font-mono uppercase tracking-wider px-6 py-2.5 inline-block"
                style={{
                  background: 'var(--navy)',
                  color: '#fff',
                  borderRadius: '4px',
                  textDecoration: 'none',
                  fontSize: '12px',
                  fontWeight: 700,
                }}
              >
                Open My Route →
              </Link>
            </div>
          )}

          <PlanViewer run={runForViewer} />
        </section>
      </DashboardLayout>
    </>
  );
}
