import Head from 'next/head';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Legend,
} from 'recharts';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import OverviewPanel from '@/components/Dashboard/OverviewPanel';
import KPIGrid from '@/components/KPICards/KPIGrid';
import MapView from '@/components/Map/MapView';
import AgentTrace from '@/components/PlanViewer/AgentTrace';
import useRuns, { useCachedRunResponse, useRunTraces } from '@/hooks/useRuns';
import { useAppContext } from '@/context/AppContext';
import {
  DEMO_MAP_FARMS,
  DEMO_MAP_MANDIS,
  DEMO_FARMS,
  DEMO_DEMAND_POINTS,
  DEMO_TRUCKS,
} from '@/utils/demoFixtures';

const TABS = [
  { id: 'overview',   label: 'OVERVIEW' },
  { id: 'farmer',     label: 'FARMER' },
  { id: 'mandi',      label: 'MANDI' },
  { id: 'transport',  label: 'TRANSPORT' },
];

// Estimated pickup times for up to 20 farms (30-min slots from 5:00 AM)
const ESTIMATED_PICKUP_TIMES = [
  '5:00 AM', '5:30 AM', '6:00 AM', '6:30 AM', '7:00 AM',
  '7:30 AM', '8:00 AM', '8:30 AM', '9:00 AM', '9:30 AM',
  '10:00 AM', '10:30 AM', '11:00 AM', '11:30 AM', '12:00 PM',
  '12:30 PM', '1:00 PM', '1:30 PM', '2:00 PM', '2:30 PM',
];

// Estimated delivery times for up to 10 mandis (1-hour slots from 10:00 AM)
const ESTIMATED_DELIVERY_TIMES = [
  '10:00 AM', '11:00 AM', '12:00 PM', '1:00 PM', '2:00 PM',
  '3:00 PM',  '4:00 PM',  '5:00 PM',  '6:00 PM', '7:00 PM',
];

export default function DashboardPage() {
  const { data: runs, loading: runsLoading } = useRuns();
  const cached     = useCachedRunResponse();
  const { currentRunId } = useAppContext();
  const runId      = cached?.run_id || currentRunId || null;
  const { data: freshTraces } = useRunTraces(runId);
  const [activeTab, setActiveTab] = useState('overview');

  const kpis   = cached?.kpis;
  const traces = (Array.isArray(freshTraces) && freshTraces.length) ? freshTraces : cached?.agent_traces;

  const routesForMap = useMemo(() => {
    const routes = cached?.plan?.route_plan?.routes || [];
    return routes
      .filter((r) => Array.isArray(r.stops) && r.stops.length > 0)
      .map((r, idx) => ({
        id: `${r.truck_id || idx}`,
        truckId: r.truck_id,
        distance_km: r.distance_km,
        stops: r.stops
          .slice()
          .sort((a, b) => (a.sequence ?? 0) - (b.sequence ?? 0))
          .map((s) => ({ lat: s.lat, lng: s.lng, label: s.label })),
      }));
  }, [cached]);

  // ── Derived data for role tabs ──────────────────────────────────────────
  const rawRoutes = useMemo(() => cached?.plan?.route_plan?.routes || [], [cached]);

  // farm_id → truck_id from route stops
  const farmTruckMap = useMemo(() => {
    const m = {};
    rawRoutes.forEach((r) => {
      (r.stops || []).forEach((s) => {
        if (s.demand_point_id == null && s.label) m[s.label] = r.truck_id;
      });
    });
    return m;
  }, [rawRoutes]);

  // demand_point_id → { truck_id, stopIdx }
  const mandiRouteMap = useMemo(() => {
    const m = {};
    rawRoutes.forEach((r) => {
      (r.stops || []).forEach((s) => {
        if (s.demand_point_id != null && !m[s.demand_point_id]) {
          m[s.demand_point_id] = { truck_id: r.truck_id, distance_km: r.distance_km };
        }
      });
    });
    return m;
  }, [rawRoutes]);

  // at_risk_stock lookup: farm_id → { hours_until_spoilage, kg_at_risk }
  const atRiskMap = useMemo(() => {
    const m = {};
    (cached?.at_risk_stock || []).forEach((s) => { m[s.farm_id] = s; });
    return m;
  }, [cached]);

  const lastRun = cached
    ? { runId: cached.run_id, createdAt: cached.plan?.created_at || new Date().toISOString() }
    : runs?.[runs.length - 1];

  return (
    <>
      <Head><title>Dashboard | AgentFarm</title></Head>
      <DashboardLayout title="Dashboard" subtitle={`Run ${runId?.slice(0, 8) || '—'}`}>
        <OverviewPanel lastRun={lastRun} />

        {cached ? <KPIGrid kpis={kpis} /> : <EmptyState />}

        {/* ── Role tabs ────────────────────────────────────────────────── */}
        {cached && (
          <>
            {/* Tab pill row */}
            <div className="mt-8 flex gap-2 flex-wrap">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className="px-4 py-2 font-mono uppercase tracking-wider transition"
                  style={{
                    fontSize: '11px',
                    letterSpacing: '0.15em',
                    borderRadius: '2px',
                    border: activeTab === tab.id ? '1px solid var(--accent)' : '1px solid var(--border)',
                    background: activeTab === tab.id ? 'rgba(245,166,35,0.1)' : 'transparent',
                    color: activeTab === tab.id ? 'var(--accent)' : 'var(--muted)',
                    cursor: 'pointer',
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* ── OVERVIEW tab ─────────────────────────────────────────── */}
            {activeTab === 'overview' && (
              <>
                {/* Waste comparison bar chart */}
                {kpis && (
                  <div className="mt-6">
                    <WasteBarChart kpis={kpis} />
                  </div>
                )}

                <section className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2">
                    <SectionCard title="▸ Optimised Routes" badge={`${routesForMap.length} ROUTES · ${DEMO_MAP_FARMS.length} FARMS · ${DEMO_MAP_MANDIS.length} MANDIS`}>
                      <MapView farms={DEMO_MAP_FARMS} demandPoints={DEMO_MAP_MANDIS} routes={routesForMap} />
                    </SectionCard>
                  </div>
                  <div className="lg:col-span-1">
                    <AgentTrace traces={traces} />
                  </div>
                </section>
              </>
            )}

            {/* ── FARMER tab ───────────────────────────────────────────── */}
            {activeTab === 'farmer' && (
              <section className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
                <SectionCard title="▸ Your Farms at Risk Today">
                  <div className="divide-y" style={{ '--tw-divide-opacity': 1, borderColor: 'var(--border)' }}>
                    {DEMO_FARMS.map((farm, idx) => {
                      const stock   = atRiskMap[farm.id];
                      const truckId = farmTruckMap[farm.id];
                      const hours   = stock?.hours_until_spoilage ?? null;
                      const kg      = stock?.kg_at_risk ?? farm.typical_yield_kg;
                      const pickupTime = ESTIMATED_PICKUP_TIMES[idx] || '7:00 AM';
                      return (
                        <div key={farm.id} className="px-5 py-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-syne font-bold text-paper" style={{ fontSize: '13px' }}>
                                🌱 {farm.name}
                              </p>
                              <p className="font-mono text-muted mt-1" style={{ fontSize: '11px' }}>
                                {kg.toLocaleString()} kg at risk
                                {hours != null ? ` · ${Math.round(hours)}h until spoilage` : ''}
                              </p>
                              {truckId && (
                                <p className="font-mono mt-1" style={{ fontSize: '11px', color: 'var(--accent)' }}>
                                  Truck assigned: {truckId} · pickup {pickupTime}
                                </p>
                              )}
                              {!truckId && (
                                <p className="font-mono mt-1" style={{ fontSize: '11px', color: 'var(--red-risk)' }}>
                                  ⚠ No truck assigned yet
                                </p>
                              )}
                            </div>
                            <UrgencyBadge hours={hours} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </SectionCard>

                <SectionCard title="▸ What To Do Today">
                  <div className="px-5 py-4 space-y-4">
                    {DEMO_FARMS.map((farm, idx) => {
                      const truckId    = farmTruckMap[farm.id];
                      const pickupTime = ESTIMATED_PICKUP_TIMES[idx] || '7:00 AM';
                      const stock      = atRiskMap[farm.id];
                      const kg         = stock?.kg_at_risk ?? farm.typical_yield_kg;
                      return (
                        <div
                          key={farm.id}
                          className="p-3"
                          style={{
                            borderLeft: '3px solid var(--accent)',
                            background: 'rgba(245,166,35,0.03)',
                            borderRadius: '0 2px 2px 0',
                          }}
                        >
                          <p className="font-mono text-paper" style={{ fontSize: '12px', lineHeight: 1.6 }}>
                            Harvest and dispatch <strong>{farm.crop_type}</strong> from{' '}
                            <strong>{farm.name}</strong> ({kg.toLocaleString()} kg) within 48h.
                            {truckId
                              ? ` Truck ${truckId} picks up at ${pickupTime}.`
                              : ' Contact transport team to assign a truck.'}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </SectionCard>
              </section>
            )}

            {/* ── MANDI tab ────────────────────────────────────────────── */}
            {activeTab === 'mandi' && (
              <section className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
                <SectionCard title="▸ Incoming Supply Today">
                  <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
                    {DEMO_DEMAND_POINTS.map((dp, idx) => {
                      const info       = mandiRouteMap[dp.id] || mandiRouteMap[dp.id.replace('point_type','type')];
                      const truckId    = info?.truck_id;
                      const truckObj   = DEMO_TRUCKS.find((t) => t.id === truckId);
                      const etaTime    = ESTIMATED_DELIVERY_TIMES[idx] || '12:00 PM';
                      // Sum kg_at_risk for farms routed to this mandi (approximate)
                      const supplyKg   = truckObj?.capacity_kg ?? dp.base_demand_per_day;
                      return (
                        <div key={dp.id} className="px-5 py-4">
                          <p className="font-syne font-bold text-paper" style={{ fontSize: '13px' }}>
                            📦 {dp.name}
                          </p>
                          <p className="font-mono text-muted mt-1" style={{ fontSize: '11px' }}>
                            {truckId
                              ? `expecting ~${Math.round(supplyKg / 2).toLocaleString()} kg tomatoes via ${truckId} · ETA ${etaTime}`
                              : 'No supply routed — check plan for details'}
                          </p>
                          <p className="font-mono mt-1" style={{ fontSize: '11px', color: 'var(--blue-mandi)' }}>
                            base demand: {dp.base_demand_per_day.toLocaleString()} kg/day
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </SectionCard>

                <SectionCard title="▸ Demand vs Supply">
                  <div className="px-5 py-4 space-y-5">
                    {DEMO_DEMAND_POINTS.map((dp, idx) => {
                      const info     = mandiRouteMap[dp.id];
                      const truckObj = DEMO_TRUCKS.find((t) => t.id === info?.truck_id);
                      const supply   = truckObj?.capacity_kg ?? 0;
                      const demand   = dp.base_demand_per_day;
                      const supplyPct = Math.min(100, (supply / Math.max(demand, 1)) * 100);
                      return (
                        <div key={dp.id}>
                          <p className="font-mono text-muted mb-2 uppercase" style={{ fontSize: '10px', letterSpacing: '0.15em' }}>
                            {dp.name}
                          </p>
                          <BarPair
                            demandKg={demand}
                            supplyKg={supply}
                            supplyPct={supplyPct}
                          />
                        </div>
                      );
                    })}
                  </div>
                </SectionCard>
              </section>
            )}

            {/* ── TRANSPORT tab ────────────────────────────────────────── */}
            {activeTab === 'transport' && (
              <section className="mt-6 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {DEMO_TRUCKS.map((truck, tIdx) => {
                    const route   = rawRoutes.find((r) => r.truck_id === truck.id);
                    const farmStops = (route?.stops || []).filter((s) => s.demand_point_id == null && s.label);
                    const dpStops   = (route?.stops || []).filter((s) => s.demand_point_id != null);
                    const farmNames = farmStops.map((s) => {
                      const f = DEMO_FARMS.find((f) => f.id === s.label);
                      return f?.name || s.label;
                    });
                    const dpNames = dpStops.map((s) => {
                      const d = DEMO_DEMAND_POINTS.find((d) => d.id === (s.demand_point_id || s.label));
                      return d?.name || s.demand_point_id || s.label;
                    });
                    const totalLoad = farmStops.reduce((sum, s) => {
                      const stock = atRiskMap[s.label];
                      return sum + (stock?.kg_at_risk ?? 0);
                    }, 0);
                    const etaTime   = ESTIMATED_DELIVERY_TIMES[tIdx] || '12:00 PM';
                    const loadPct   = Math.min(100, (totalLoad / truck.capacity_kg) * 100);

                    return (
                      <div
                        key={truck.id}
                        className="p-5"
                        style={{
                          border: '1px solid var(--border)',
                          borderTop: '3px solid var(--purple-log)',
                          borderRadius: '4px',
                          background: 'var(--bg-card)',
                        }}
                      >
                        <div className="flex items-center justify-between mb-3">
                          <p className="font-syne font-bold uppercase tracking-wider text-paper" style={{ fontSize: '14px' }}>
                            🚚 Truck {truck.id}
                          </p>
                          <span className="font-mono text-muted" style={{ fontSize: '11px' }}>
                            {truck.capacity_kg.toLocaleString()} kg cap
                          </span>
                        </div>

                        {route ? (
                          <>
                            <p className="font-mono text-muted" style={{ fontSize: '11px', lineHeight: 1.6 }}>
                              Route:{' '}
                              <span style={{ color: 'var(--text)' }}>
                                {farmNames.join(' → ')}
                                {dpNames.length > 0 && ` → ${dpNames.join(' → ')}`}
                              </span>
                            </p>
                            <p className="font-mono text-muted mt-1" style={{ fontSize: '11px' }}>
                              Distance: ~{Math.round(route.distance_km || 0)} km
                              &nbsp;·&nbsp; ETA {etaTime}
                              &nbsp;·&nbsp; {Math.round(totalLoad).toLocaleString()} kg loaded
                            </p>
                            {/* Load bar */}
                            <div className="mt-3">
                              <div className="flex justify-between font-mono text-muted mb-1" style={{ fontSize: '10px' }}>
                                <span>LOAD</span>
                                <span>{Math.round(totalLoad).toLocaleString()} / {truck.capacity_kg.toLocaleString()} kg</span>
                              </div>
                              <div style={{ height: '4px', background: 'var(--border)', borderRadius: '2px', overflow: 'hidden' }}>
                                <div style={{
                                  width: `${loadPct}%`,
                                  height: '100%',
                                  background: loadPct > 90 ? 'var(--red-risk)' : 'var(--purple-log)',
                                  transition: 'width 0.4s ease',
                                }} />
                              </div>
                            </div>
                          </>
                        ) : (
                          <p className="font-mono text-muted" style={{ fontSize: '11px' }}>
                            No route assigned in this plan.
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Map below truck cards */}
                <SectionCard title="▸ Route Map" badge={`${routesForMap.length} ACTIVE ROUTES`}>
                  <MapView farms={DEMO_MAP_FARMS} demandPoints={DEMO_MAP_MANDIS} routes={routesForMap} />
                </SectionCard>
              </section>
            )}
          </>
        )}

        {/* ── Recent Runs ──────────────────────────────────────────────── */}
        <section
          className="mt-8 bg-card"
          style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
        >
          <div
            className="px-5 py-3 flex items-baseline justify-between"
            style={{ borderBottom: '1px solid var(--border)' }}
          >
            <h2 className="font-syne font-bold uppercase text-paper tracking-wider-2" style={{ fontSize: '14px' }}>
              ▸ Recent Runs
            </h2>
            <Link href="/runs" className="font-mono text-accent text-[11px] tracking-wider uppercase hover:underline">
              View all →
            </Link>
          </div>
          {runsLoading ? (
            <p className="px-5 py-4 font-mono text-muted text-[12px]">Loading…</p>
          ) : runs.length === 0 ? (
            <p className="px-5 py-4 font-mono text-muted text-[12px] italic">
              No runs yet.{' '}
              <Link href="/scenario" className="text-accent hover:underline">Run one</Link>.
            </p>
          ) : (
            <ul>
              {runs.map((r, idx) => (
                <li
                  key={r.runId}
                  className="px-5 py-3 flex justify-between items-center"
                  style={{ borderTop: idx === 0 ? 'none' : '1px solid var(--border)' }}
                >
                  <div>
                    <p className="font-syne font-bold text-paper" style={{ fontSize: '13px', letterSpacing: '0.05em' }}>
                      {r.runId?.slice(0, 16)}…
                    </p>
                    <p className="font-mono text-muted text-[11px] mt-1 uppercase tracking-wider">
                      {r.scenarioType}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-muted text-[11px]">{r.createdAt}</p>
                    <p className="font-syne font-bold mt-1" style={{ color: 'var(--green-ok)', fontSize: '12px' }}>
                      ↑ {(r.wasteReductionPct * 100).toFixed(1)}% waste reduction
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </DashboardLayout>
    </>
  );
}

/* ── Sub-components ─────────────────────────────────────────────────────── */

function EmptyState() {
  return (
    <div
      className="bg-card p-8 text-center font-mono text-muted text-[13px]"
      style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
    >
      No scenario has been run yet.{' '}
      <Link href="/scenario" className="text-accent hover:underline tracking-wider-2">
        RUN A SCENARIO
      </Link>{' '}
      to populate KPIs, routes, and traces.
    </div>
  );
}

function SectionCard({ title, badge, children }) {
  return (
    <div
      className="bg-card overflow-hidden"
      style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
    >
      <div
        className="px-5 py-3 flex items-baseline justify-between"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <h2 className="font-syne font-bold uppercase text-paper tracking-wider-2" style={{ fontSize: '14px' }}>
          {title}
        </h2>
        {badge && (
          <span className="font-mono text-muted text-[11px] tracking-wider">{badge}</span>
        )}
      </div>
      {children}
    </div>
  );
}

function UrgencyBadge({ hours }) {
  if (hours == null) return null;
  const color = hours <= 0 ? 'var(--red-risk)' : hours <= 12 ? '#FF9800' : 'var(--green-ok)';
  const label = hours <= 0 ? 'OVERDUE' : hours <= 12 ? 'URGENT' : 'OK';
  return (
    <span
      className="font-mono uppercase shrink-0"
      style={{
        fontSize: '10px',
        letterSpacing: '0.15em',
        color,
        border: `1px solid ${color}`,
        borderRadius: '2px',
        padding: '2px 6px',
      }}
    >
      {label}
    </span>
  );
}

function BarPair({ demandKg, supplyKg, supplyPct }) {
  return (
    <div className="space-y-2">
      <div>
        <div className="flex justify-between font-mono text-muted mb-1" style={{ fontSize: '10px' }}>
          <span>DEMAND</span>
          <span>{demandKg.toLocaleString()} kg/day</span>
        </div>
        <div style={{ height: '6px', background: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
          <div style={{ width: '100%', height: '100%', background: 'var(--blue-mandi)' }} />
        </div>
      </div>
      <div>
        <div className="flex justify-between font-mono text-muted mb-1" style={{ fontSize: '10px' }}>
          <span>SUPPLY</span>
          <span>{supplyKg ? supplyKg.toLocaleString() : '—'} kg</span>
        </div>
        <div style={{ height: '6px', background: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
          <div
            style={{
              width: `${supplyPct}%`,
              height: '100%',
              background: supplyPct >= 90 ? 'var(--green-ok)' : supplyPct >= 50 ? 'var(--orange-dmd)' : 'var(--red-risk)',
              transition: 'width 0.4s ease',
            }}
          />
        </div>
      </div>
    </div>
  );
}

/* ── Waste Comparison Bar Chart ─────────────────────────────────────────── */
function WasteBarChart({ kpis }) {
  const naiveKg     = Number(kpis?.naive_waste_kg     ?? 0);
  const optimizedKg = Number(kpis?.optimized_waste_kg ?? 0);
  const wastePct    = Number(kpis?.waste_reduction_pct ?? 0);

  const data = [
    { label: 'Naive',     kg: naiveKg,     fill: '#FF4444' },
    { label: 'Optimised', kg: optimizedKg, fill: '#4CAF50' },
  ];

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    return (
      <div
        className="font-mono"
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: '4px',
          padding: '8px 12px',
          fontSize: '11px',
          color: 'var(--text)',
        }}
      >
        <p style={{ color: 'var(--muted)' }}>{payload[0].payload.label}</p>
        <p style={{ color: payload[0].fill, fontWeight: 700 }}>
          {Number(payload[0].value).toLocaleString()} kg waste
        </p>
      </div>
    );
  };

  return (
    <div
      className="bg-card"
      style={{ border: '1px solid var(--border)', borderRadius: '4px', overflow: 'hidden' }}
    >
      <div
        className="px-5 py-3 flex items-baseline justify-between"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <h2 className="font-syne font-bold uppercase text-paper tracking-wider-2" style={{ fontSize: '14px' }}>
          ▸ Waste Reduction — Naive vs Optimised
        </h2>
        <span className="font-mono" style={{ fontSize: '11px', color: 'var(--green-ok)' }}>
          {wastePct.toFixed(1)}% reduction vs baseline
        </span>
      </div>
      <div className="px-5 py-4" style={{ height: '180px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barCategoryGap="40%" margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <XAxis
              dataKey="label"
              tick={{ fill: 'var(--muted)', fontFamily: 'DM Mono', fontSize: 11 }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: 'var(--muted)', fontFamily: 'DM Mono', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v} kg`}
              width={60}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            <Bar dataKey="kg" radius={[2, 2, 0, 0]}>
              {data.map((entry) => (
                <Cell key={entry.label} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="px-5 pb-4 flex gap-6">
        <LegendDot color="#FF4444" label={`Naive baseline: ${naiveKg.toLocaleString()} kg`} />
        <LegendDot color="#4CAF50" label={`After VRP: ${optimizedKg.toLocaleString()} kg`} />
      </div>
    </div>
  );
}

function LegendDot({ color, label }) {
  return (
    <div className="flex items-center gap-2">
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }} />
      <span className="font-mono text-muted" style={{ fontSize: '11px' }}>{label}</span>
    </div>
  );
}
