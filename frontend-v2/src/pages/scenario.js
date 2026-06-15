import Head from 'next/head';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import ScenarioForm from '@/components/ScenarioBuilder/ScenarioForm';
import FarmEconomicsPanel from '@/components/Farmer/FarmEconomicsPanel';
import TruckGapAlertPanel from '@/components/Dashboard/TruckGapAlertPanel';
import MapView from '@/components/Map/MapView';
import SimulationPanel from '@/components/AgentSimulation/SimulationPanel';
import WeatherSourceBanner from '@/components/Dashboard/WeatherSourceBanner';
import { checkTruckGap } from '@/api/client';
import {
  DEMO_MAP_FARMS,
  DEMO_MAP_MANDIS,
  DEMO_FARMS,
  DEMO_DEMAND_POINTS,
  DEMO_TRUCKS,
} from '@/utils/demoFixtures';

const TOTAL_CAPACITY = DEMO_TRUCKS.reduce((s, t) => s + t.capacity_kg, 0);

const NETWORK_KPIS = [
  { label: 'Farms', value: DEMO_FARMS.length, sub: 'Karnataka + Maharashtra', accent: 'var(--green-ok)' },
  { label: 'Mandis', value: DEMO_DEMAND_POINTS.length, sub: 'APMC · private · retail', accent: 'var(--blue-mandi)' },
  { label: 'Trucks', value: DEMO_TRUCKS.length, sub: 'Registered fleet', accent: 'var(--accent)' },
  { label: 'Capacity', value: `${(TOTAL_CAPACITY / 1000).toFixed(0)}t`, sub: `${TOTAL_CAPACITY.toLocaleString()} kg total`, accent: 'var(--navy)' },
];

/**
 * Scenario page — state machine:
 *
 *   idle        Form + map preview shown
 *   running     API call in flight; SimulationPanel shows all agents PENDING
 *   simulating  API returned; SimulationPanel animates traces one by one
 *   done        Animation finished; show summary card + "View Dashboard →"
 */
export default function ScenarioPage() {
  const [simState, setSimState]       = useState('idle');
  const [simTraces, setSimTraces]     = useState([]);
  const [apiResult, setApiResult]     = useState(null);
  const [elapsedMs, setElapsedMs]     = useState(null);
  const [simError, setSimError]       = useState(null);
  const [selectedType, setSelectedType] = useState('monsoon_disruption');
  const [truckGap, setTruckGap]       = useState(null);
  const startRef = useRef(null);

  useEffect(() => {
    if (!Array.isArray(DEMO_FARMS) || DEMO_FARMS.length === 0) return;
    if (!Array.isArray(DEMO_TRUCKS) || DEMO_TRUCKS.length === 0) return;
    checkTruckGap({ farms: DEMO_FARMS, trucks: DEMO_TRUCKS })
      .then(setTruckGap)
      .catch(() => setTruckGap(null));
  }, []);

  const handleRunStart = (scenarioType) => {
    if (scenarioType) setSelectedType(scenarioType);
    startRef.current = Date.now();
    setSimState('running');
  };

  const handleRunComplete = (result) => {
    const elapsed = startRef.current ? Date.now() - startRef.current : null;
    setElapsedMs(elapsed);
    setApiResult(result);
    setSimTraces(result?.agent_traces || []);
    if (result?.calendar_alert) {
      setTruckGap(result.calendar_alert);
    }
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
    setSelectedType('monsoon_disruption');
    startRef.current = null;
  };

  /* ── Idle: scenario builder + map ──────────────────────────────────── */
  if (simState === 'idle') {
    return (
      <>
        <Head><title>Scenario | AgentFarm</title></Head>
        <DashboardLayout
          title="Run a Scenario"
          subtitle="Configure disruption · review network · launch agent pipeline"
        >
          <div className="space-y-6 max-w-[1400px]">
            {/* Hero + network KPIs */}
            <div
              className="p-5 md:p-6"
              style={{
                border: '1px solid var(--border)',
                borderRadius: '4px',
                background: 'linear-gradient(135deg, var(--accent-muted) 0%, var(--orange-muted) 100%)',
              }}
            >
              <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 mb-5">
                <div>
                  <p
                    className="font-mono uppercase mb-2"
                    style={{ color: 'var(--green-ok)', fontSize: '10px', letterSpacing: '0.16em' }}
                  >
                    FPO Scenario Builder
                  </p>
                  <h2
                    className="font-syne font-bold"
                    style={{ fontSize: '22px', color: 'var(--navy)', lineHeight: 1.25 }}
                  >
                    Plan today&apos;s supply chain under disruption
                  </h2>
                  <p className="font-mono text-muted mt-2 max-w-xl" style={{ fontSize: '12px', lineHeight: 1.6 }}>
                    Six agents forecast demand, flag at-risk stock, and optimise routes across your demo network.
                    Pick a scenario and run.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {NETWORK_KPIS.map((kpi) => (
                  <div
                    key={kpi.label}
                    className="p-4"
                    style={{
                      border: '1px solid var(--border)',
                      borderTop: `3px solid ${kpi.accent}`,
                      borderRadius: '4px',
                      background: 'var(--bg-card)',
                    }}
                  >
                    <p
                      className="font-mono uppercase text-muted"
                      style={{ fontSize: '9px', letterSpacing: '0.12em' }}
                    >
                      {kpi.label}
                    </p>
                    <p
                      className="font-syne font-bold mt-1"
                      style={{ fontSize: '1.65rem', color: kpi.accent, lineHeight: 1 }}
                    >
                      {kpi.value}
                    </p>
                    <p className="font-mono text-muted mt-1" style={{ fontSize: '10px' }}>
                      {kpi.sub}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <TruckGapAlertPanel analysis={truckGap} />

            {/* Main builder + map */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
              <div className="xl:col-span-5 space-y-0">
                <div
                  className="p-5 md:p-6"
                  style={{
                    border: '1px solid var(--border)',
                    borderTop: '3px solid var(--accent)',
                    borderRadius: '4px',
                    background: 'var(--bg-card)',
                  }}
                >
                  <ScenarioForm
                    onRunStart={handleRunStart}
                    onComplete={handleRunComplete}
                    onError={handleRunError}
                  />
                </div>
              </div>

              <div className="xl:col-span-7 xl:sticky xl:top-[88px]">
                <div
                  className="overflow-hidden"
                  style={{
                    border: '1px solid var(--border)',
                    borderRadius: '4px',
                    background: 'var(--bg-card)',
                  }}
                >
                  <div
                    className="px-5 py-3 flex items-baseline justify-between"
                    style={{ borderBottom: '1px solid var(--border)' }}
                  >
                    <div>
                      <h3
                        className="font-syne font-bold uppercase tracking-wider text-paper"
                        style={{ fontSize: '13px' }}
                      >
                        Network Preview
                      </h3>
                      <p className="font-mono text-muted mt-0.5" style={{ fontSize: '10px' }}>
                        Farms, mandis, and routes appear here after a run
                      </p>
                    </div>
                    <span
                      className="font-mono uppercase px-2 py-0.5"
                      style={{
                        fontSize: '9px',
                        letterSpacing: '0.1em',
                        color: 'var(--muted)',
                        border: '1px solid var(--border)',
                        borderRadius: '2px',
                      }}
                    >
                      Pre-run
                    </span>
                  </div>
                  <MapView farms={DEMO_MAP_FARMS} demandPoints={DEMO_MAP_MANDIS} routes={[]} />
                </div>
              </div>
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
                background: 'var(--red-muted)',
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
                  color: 'var(--accent-text)',
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
  const activeType    = apiResult?.scenario_type || selectedType;
  const scenarioLabel = activeType.replace(/_/g, ' ').toUpperCase();
  const wastePct      = apiResult?.kpis?.waste_reduction_pct ?? 0;
  const coveredCount  = apiResult?.kpis?.covered_count       ?? 0;
  const routeCount    = apiResult?.kpis?.route_count         ?? 0;
  const elapsedSec    = elapsedMs != null ? (elapsedMs / 1000).toFixed(1) : null;

  return (
    <>
      <Head><title>Running Scenario | AgentFarm</title></Head>
      <DashboardLayout
        title={simState === 'done' ? 'Plan Ready' : 'Agents Running'}
        subtitle={
          simState === 'done'
            ? '5 core agents + orchestrator · scenario complete'
            : 'Pipeline: 6 agents executing (5 core + orchestrator)'
        }
      >
        <div className="max-w-5xl mx-auto space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: status + simulation */}
            <div className="lg:col-span-2 space-y-6">
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

              {apiResult?.weather_summary && (
                <WeatherSourceBanner weatherSummary={apiResult.weather_summary} />
              )}

              <TruckGapAlertPanel analysis={truckGap || apiResult?.calendar_alert} />

              <SimulationPanel
                traces={simTraces}
                isRunning={simState !== 'done'}
                scenarioType={activeType}
                onComplete={handleSimComplete}
              />

              {simState === 'done' && apiResult && (
                <FarmEconomicsPanel compact cachedRun={apiResult} />
              )}
            </div>

            {/* Right: live stats sidebar */}
            <div className="space-y-4">
              <div
                className="p-5 space-y-4"
                style={{
                  border: '1px solid var(--border)',
                  borderRadius: '4px',
                  background: 'var(--bg-card)',
                  position: 'sticky',
                  top: 88,
                }}
              >
                <p
                  className="font-mono uppercase"
                  style={{ color: 'var(--muted)', fontSize: '9px', letterSpacing: '0.14em' }}
                >
                  Run status
                </p>

                <div className="space-y-3">
                  <StatusRow label="Scenario" value={scenarioLabel} />
                  <StatusRow
                    label="Phase"
                    value={
                      simState === 'running'
                        ? 'Backend'
                        : simState === 'simulating'
                          ? 'Replay'
                          : 'Complete'
                    }
                    accent={simState === 'done' ? 'var(--green-ok)' : 'var(--accent)'}
                  />
                  {elapsedSec && (
                    <StatusRow label="Elapsed" value={`${elapsedSec}s`} />
                  )}
                </div>

                {simState === 'done' && (
                  <>
                    <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
                      <p
                        className="font-mono uppercase mb-3"
                        style={{ color: 'var(--green-ok)', fontSize: '9px', letterSpacing: '0.14em' }}
                      >
                        Plan KPIs
                      </p>
                      <div className="space-y-3">
                        <StatChip
                          label="waste reduction"
                          value={`${Number(wastePct).toFixed(1)}%`}
                          accent="var(--green-ok)"
                          compact
                        />
                        <StatChip
                          label="farms covered"
                          value={String(Math.round(coveredCount))}
                          compact
                        />
                        <StatChip
                          label="routes"
                          value={String(Math.round(routeCount))}
                          compact
                        />
                      </div>
                    </div>

                    <div className="flex flex-col gap-2 pt-2">
                      <Link
                        href="/dashboard"
                        className="px-4 py-3 font-mono uppercase tracking-wider-2 text-center"
                        style={{
                          background: 'var(--accent)',
                          color: 'var(--accent-text)',
                          fontSize: '11px',
                          fontWeight: 600,
                          borderRadius: '4px',
                          letterSpacing: '0.15em',
                        }}
                      >
                        View Dashboard →
                      </Link>
                      <button
                        onClick={handleReset}
                        className="px-4 py-2.5 font-mono uppercase tracking-wider-2 hover:text-accent hover:border-accent transition"
                        style={{
                          color: 'var(--muted)',
                          border: '1px solid var(--border)',
                          fontSize: '10px',
                          borderRadius: '4px',
                          letterSpacing: '0.15em',
                          background: 'transparent',
                        }}
                      >
                        Run Another
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {simState === 'done' && (
            <div
              className="p-5"
              style={{
                border: '1px solid var(--border)',
                borderTop: '3px solid var(--green-ok)',
                borderRadius: '4px',
                background: 'var(--bg-card)',
              }}
            >
              <p className="font-mono" style={{ fontSize: '12px', color: 'var(--green-ok)', lineHeight: 1.55 }}>
                Pipeline completed — Weather, Demand, Inventory, Logistics, Validator, and Orchestrator agents finished.
                {Math.round(routeCount)} route{routeCount !== 1 ? 's' : ''} dispatched ·{' '}
                {Math.round(coveredCount)} at-risk farms covered ·{' '}
                {Number(wastePct).toFixed(1)}% waste reduction vs naive baseline.
              </p>
            </div>
          )}
        </div>
      </DashboardLayout>
    </>
  );
}

function StatusRow({ label, value, accent }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="font-mono uppercase text-muted" style={{ fontSize: '9px', letterSpacing: '0.1em' }}>
        {label}
      </span>
      <span
        className="font-syne font-bold text-right truncate"
        style={{ fontSize: '12px', color: accent || 'var(--text)' }}
      >
        {value}
      </span>
    </div>
  );
}

function StatChip({ label, value, accent, compact }) {
  return (
    <div
      className="p-3 flex items-center justify-between gap-3"
      style={{
        border: '1px solid var(--border)',
        borderRadius: '4px',
        background: 'var(--bg)',
      }}
    >
      <p className="font-mono text-muted uppercase" style={{ fontSize: compact ? '9px' : '10px', letterSpacing: '0.12em' }}>
        {label}
      </p>
      <p
        className="font-syne font-bold"
        style={{ fontSize: compact ? '16px' : '20px', color: accent || 'var(--text)' }}
      >
        {value}
      </p>
    </div>
  );
}
