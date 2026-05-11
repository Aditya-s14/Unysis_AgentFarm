import Head from 'next/head';
import Link from 'next/link';
import { useRef, useState } from 'react';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import ScenarioForm from '@/components/ScenarioBuilder/ScenarioForm';
import MapView from '@/components/Map/MapView';
import SimulationPanel from '@/components/AgentSimulation/SimulationPanel';
import {
  DEMO_MAP_FARMS,
  DEMO_MAP_MANDIS,
  DEMO_FARMS,
  DEMO_DEMAND_POINTS,
  DEMO_TRUCKS,
} from '@/utils/demoFixtures';

/**
 * Scenario page — state machine:
 *
 *   idle        Form + map preview shown
 *   running     API call in flight; SimulationPanel shows all agents PENDING
 *   simulating  API returned; SimulationPanel animates traces one by one
 *   done        Animation finished; show summary card + "View Dashboard →"
 */
export default function ScenarioPage() {
  const [simState, setSimState]   = useState('idle');   // 'idle' | 'running' | 'simulating' | 'done' | 'error'
  const [simTraces, setSimTraces] = useState([]);
  const [apiResult, setApiResult] = useState(null);
  const [elapsedMs, setElapsedMs] = useState(null);
  const [simError, setSimError]   = useState(null);
  const startRef = useRef(null);

  const handleRunStart = () => {
    startRef.current = Date.now();
    setSimState('running');
  };

  const handleRunComplete = (result) => {
    const elapsed = startRef.current ? Date.now() - startRef.current : null;
    setElapsedMs(elapsed);
    setApiResult(result);
    setSimTraces(result?.agent_traces || []);
    setSimState('simulating');
  };

  const handleSimComplete = () => {
    setSimState('done');
  };

  const handleRunError = (err) => {
    const msg = err?.response?.data?.detail
      || err?.message
      || 'Unknown error';
    setSimError(msg);
    setSimState('error');
  };

  const handleReset = () => {
    setSimState('idle');
    setSimTraces([]);
    setApiResult(null);
    setElapsedMs(null);
    setSimError(null);
    startRef.current = null;
  };

  /* ── Idle: original form + map ───────────────────────────────────────── */
  if (simState === 'idle') {
    return (
      <>
        <Head><title>Scenario | AgentFarm</title></Head>
        <DashboardLayout title="Run a Scenario" subtitle={`${DEMO_FARMS.length} farms · ${DEMO_DEMAND_POINTS.length} mandis · ${DEMO_TRUCKS.length} trucks`}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
              <ScenarioForm
                onRunStart={handleRunStart}
                onComplete={handleRunComplete}
                onError={handleRunError}
              />
            </div>
            <div className="lg:col-span-2">
              <MapView farms={DEMO_MAP_FARMS} demandPoints={DEMO_MAP_MANDIS} routes={[]} />
            </div>
          </div>
        </DashboardLayout>
      </>
    );
  }

  /* ── Error: pipeline call failed ─────────────────────────────────────── */
  if (simState === 'error') {
    return (
      <>
        <Head><title>Scenario Error | AgentFarm</title></Head>
        <DashboardLayout title="Pipeline Error" subtitle="Something went wrong">
          <div className="max-w-2xl mx-auto">
            <div
              className="p-6 space-y-4"
              style={{
                border: '1px solid var(--red-risk)',
                borderTop: '3px solid var(--red-risk)',
                borderRadius: '4px',
                background: 'rgba(255, 68, 68, 0.04)',
              }}
            >
              <div className="flex items-start gap-3">
                <span style={{ fontSize: '20px', lineHeight: 1 }}>⚠</span>
                <div>
                  <p
                    className="font-syne font-bold uppercase tracking-wider-2"
                    style={{ fontSize: '14px', color: 'var(--red-risk)' }}
                  >
                    Pipeline error
                  </p>
                  <p className="font-mono mt-2" style={{ fontSize: '12px', color: 'var(--muted)' }}>
                    Check that the backend is running at{' '}
                    <span style={{ color: 'var(--text)' }}>localhost:8000</span>
                  </p>
                </div>
              </div>

              {simError && (
                <div
                  className="font-mono p-3"
                  style={{
                    fontSize: '11px',
                    color: 'var(--red-risk)',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: '2px',
                    wordBreak: 'break-word',
                  }}
                >
                  {simError}
                </div>
              )}

              <div
                className="font-mono p-3"
                style={{
                  fontSize: '11px',
                  color: 'var(--muted)',
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: '2px',
                }}
              >
                <p className="uppercase mb-2" style={{ color: 'var(--accent)', fontSize: '10px', letterSpacing: '0.15em' }}>
                  ▸ Checklist
                </p>
                <p>• docker compose ps — all 4 containers should be healthy</p>
                <p>• docker compose logs backend — look for startup errors</p>
                <p>• .env file — OPENAI_API_KEY must be set for LLM agents</p>
                <p>• curl http://localhost:8000/health — should return {`{"status":"ok"}`}</p>
              </div>

              <button
                onClick={handleReset}
                className="px-5 py-3 font-mono uppercase tracking-wider-2 transition"
                style={{
                  background: 'var(--accent)',
                  color: '#0D1F0F',
                  fontSize: '12px',
                  fontWeight: 600,
                  borderRadius: '2px',
                  letterSpacing: '0.15em',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                Try Again →
              </button>
            </div>
          </div>
        </DashboardLayout>
      </>
    );
  }

  /* ── Running / simulating / done ─────────────────────────────────────── */
  const scenarioLabel = apiResult?.scenario_type?.replace(/_/g, ' ').toUpperCase() || 'MONSOON DISRUPTION';
  const wastePct      = apiResult?.kpis?.waste_reduction_pct ?? 0;
  const coveredCount  = apiResult?.kpis?.covered_count       ?? 0;
  const routeCount    = apiResult?.kpis?.route_count         ?? 0;
  const elapsedSec    = elapsedMs != null ? (elapsedMs / 1000).toFixed(1) : null;

  return (
    <>
      <Head><title>Running Scenario | AgentFarm</title></Head>
      <DashboardLayout
        title={simState === 'done' ? 'Plan Ready' : 'Agents Running'}
        subtitle={simState === 'done' ? 'Scenario complete' : '6 autonomous agents optimising supply chain...'}
      >
        <div className="max-w-2xl mx-auto space-y-6">

          {/* ── Header label while running ── */}
          {simState !== 'done' && (
            <div
              className="px-5 py-4"
              style={{
                border: '1px solid var(--border)',
                borderTop: '3px solid var(--accent)',
                borderRadius: '4px',
                background: 'var(--bg-card)',
              }}
            >
              <p
                className="font-mono uppercase mb-1"
                style={{ color: 'var(--accent)', fontSize: '0.65rem', letterSpacing: '0.2em' }}
              >
                ▸ scenario in progress
              </p>
              <p className="font-syne font-bold uppercase tracking-wider-2" style={{ fontSize: '15px' }}>
                {scenarioLabel}
              </p>
              <p className="font-mono text-muted mt-1" style={{ fontSize: '11px' }}>
                {simState === 'running'
                  ? 'Waiting for backend pipeline to respond (~30s)...'
                  : 'Replaying agent execution trace...'}
              </p>
            </div>
          )}

          {/* ── Simulation panel ── */}
          <SimulationPanel
            traces={simTraces}
            isRunning={simState !== 'done'}
            onComplete={handleSimComplete}
          />

          {/* ── Done: summary card + CTA ── */}
          {simState === 'done' && (
            <div
              className="p-6 space-y-4"
              style={{
                border: '1px solid var(--border)',
                borderTop: '3px solid var(--green-ok)',
                borderRadius: '4px',
                background: 'var(--bg-card)',
              }}
            >
              <p
                className="font-mono uppercase"
                style={{ color: 'var(--green-ok)', fontSize: '0.65rem', letterSpacing: '0.2em' }}
              >
                ▸ plan generated successfully
              </p>

              <div className="grid grid-cols-3 gap-4">
                <StatChip
                  label="elapsed"
                  value={elapsedSec ? `${elapsedSec}s` : '—'}
                />
                <StatChip
                  label="waste reduction"
                  value={`${Number(wastePct).toFixed(1)}%`}
                  accent="var(--green-ok)"
                />
                <StatChip
                  label="farms covered"
                  value={`${Math.round(coveredCount)} / ${Math.round(coveredCount) || '—'}`}
                />
              </div>

              <p className="font-mono text-muted" style={{ fontSize: '12px' }}>
                {Math.round(routeCount)} route{routeCount !== 1 ? 's' : ''} dispatched &nbsp;·&nbsp;
                {Math.round(coveredCount)} at-risk farms covered &nbsp;·&nbsp;
                {Number(wastePct).toFixed(1)}% waste reduction vs naive baseline
              </p>

              <div className="flex gap-3 pt-2">
                <Link
                  href="/dashboard"
                  className="px-5 py-3 font-mono uppercase tracking-wider-2"
                  style={{
                    background: 'var(--accent)',
                    color: '#0D1F0F',
                    fontSize: '12px',
                    fontWeight: 600,
                    borderRadius: '2px',
                    letterSpacing: '0.15em',
                  }}
                >
                  View Dashboard →
                </Link>
                <button
                  onClick={handleReset}
                  className="px-5 py-3 font-mono uppercase tracking-wider-2 hover:text-accent hover:border-accent transition"
                  style={{
                    color: 'var(--muted)',
                    border: '1px solid var(--border)',
                    fontSize: '12px',
                    borderRadius: '2px',
                    letterSpacing: '0.15em',
                    background: 'transparent',
                  }}
                >
                  Run Another
                </button>
              </div>
            </div>
          )}
        </div>
      </DashboardLayout>
    </>
  );
}

function StatChip({ label, value, accent }) {
  return (
    <div
      className="p-3 text-center"
      style={{
        border: '1px solid var(--border)',
        borderRadius: '4px',
        background: 'var(--bg)',
      }}
    >
      <p
        className="font-syne font-bold"
        style={{ fontSize: '20px', color: accent || 'var(--text)', letterSpacing: '0.05em' }}
      >
        {value}
      </p>
      <p className="font-mono text-muted mt-1 uppercase" style={{ fontSize: '10px', letterSpacing: '0.15em' }}>
        {label}
      </p>
    </div>
  );
}
