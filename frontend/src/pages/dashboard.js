import Head from 'next/head';
import Link from 'next/link';
import { useMemo, useRef, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Legend,
} from 'recharts';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import OverviewPanel from '@/components/Dashboard/OverviewPanel';
import WeatherRiskPanel from '@/components/Dashboard/WeatherRiskPanel';
import KPIGrid from '@/components/KPICards/KPIGrid';
import { resolveWeatherPanel } from '@/utils/weatherSummary';
import MapView from '@/components/Map/MapView';
import TruckCard from '@/components/Transport/TruckCard';
import { displayTruckId } from '@/utils/truckDisplay';
import { EM_DASH, MIDDOT, SECTION, WARN } from '@/utils/uiChars';
import useRuns, { useCachedRunResponse } from '@/hooks/useRuns';
import { useAppContext } from '@/context/AppContext';
import {
  DEMO_MAP_FARMS,
  DEMO_MAP_MANDIS,
  DEMO_FARMS,
  DEMO_DEMAND_POINTS,
  DEMO_TRUCKS,
} from '@/utils/demoFixtures';
import {
  getDemandPointsFromCache,
  buildMandiFulfilmentRows,
  summarizeMandiFulfilment,
  buildSupplySuggestions,
} from '@/utils/mandiFulfilment';
import MandiSummaryGrid from '@/components/Mandi/MandiSummaryGrid';
import MandiRiskHighlights from '@/components/Mandi/MandiRiskHighlights';
import MandiFulfilmentCard from '@/components/Mandi/MandiFulfilmentCard';

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

const CROP_FILTER_OPTIONS = ['tomato', 'onion', 'mango', 'banana'];

const MANDI_STATUS_GROUPS = {
  shortage: ['CRITICAL SHORTAGE', 'SHORTAGE'],
  nearly_met: ['NEARLY MET'],
  supply_met: ['SUPPLY MET'],
  excess: ['EXCESS'],
};

const DELAYED_DISTANCE_KM = 250;

function getFarmRiskLevel(farmId, atRiskMap) {
  const stock = atRiskMap[farmId];
  if (!stock) return 'normal';
  const match = (stock.reason || '').match(/weather=(\w+)/);
  if (match) return match[1];
  const hours = stock.hours_until_spoilage;
  if (hours != null && hours < 24) return 'severe';
  if (hours != null && hours < 48) return 'warning';
  return 'normal';
}

function matchesSpoilageWindow(hours, windowKey) {
  if (windowKey === 'all') return true;
  if (hours == null) return windowKey === 'gt72';
  if (windowKey === 'lt24') return hours < 24;
  if (windowKey === '24-48') return hours >= 24 && hours < 48;
  if (windowKey === '48-72') return hours >= 48 && hours < 72;
  if (windowKey === 'gt72') return hours >= 72;
  return true;
}

function matchesCoverageRange(pct, rangeKey) {
  if (rangeKey === 'all') return true;
  if (rangeKey === 'lt50') return pct < 50;
  if (rangeKey === '50-80') return pct >= 50 && pct < 80;
  if (rangeKey === '80-100') return pct >= 80 && pct <= 100;
  if (rangeKey === 'gt100') return pct > 100;
  return true;
}

function matchesLoadUtilization(loadPct, rangeKey) {
  if (rangeKey === 'all') return true;
  if (rangeKey === 'lt50') return loadPct < 50;
  if (rangeKey === '50-80') return loadPct >= 50 && loadPct < 80;
  if (rangeKey === '80-100') return loadPct >= 80;
  return true;
}

function isTruckDelayed(distanceKm, route) {
  return Boolean(route) && distanceKm >= DELAYED_DISTANCE_KM;
}

export default function DashboardPage() {
  const { data: runs, loading: runsLoading } = useRuns();
  const cached     = useCachedRunResponse();
  const { currentRunId } = useAppContext();
  const runId      = cached?.run_id || currentRunId || null;
  const [activeTab, setActiveTab]           = useState('overview');
  const [selectedTruckId, setSelectedTruckId] = useState(null);
  const [farmerFilters, setFarmerFilters] = useState({
    risk: 'all', crop: 'all', truck: 'all', spoilage: 'all',
  });
  const [mandiFilters, setMandiFilters] = useState({
    status: 'all', coverage: 'all', search: '',
  });
  const [transportFilters, setTransportFilters] = useState({
    status: 'all', mandi: 'all', load: 'all',
  });
  const mapPanelRef = useRef(null);

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
  };

  const handleTruckSelect = (truckId) => {
    setSelectedTruckId((prev) => (prev === truckId ? null : truckId));
    mapPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const kpis   = cached?.kpis;

  const routesForMap = useMemo(() => {
    const routes = cached?.plan?.route_plan?.routes || [];
    return routes
      .filter((r) => Array.isArray(r.stops) && r.stops.length > 0)
      .map((r, idx) => ({
        id: `${r.truck_id || idx}`,
        truckId: r.truck_id,
        distance_km: r.distance_km,
        geometry: r.geometry || null,
        stops: r.stops
          .slice()
          .sort((a, b) => (a.sequence ?? 0) - (b.sequence ?? 0))
          .map((s) => ({ lat: s.lat, lng: s.lng, label: s.label })),
      }));
  }, [cached]);

  const routeTruckIds = useMemo(
    () => routesForMap.map((r) => r.truckId).filter(Boolean),
    [routesForMap],
  );

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

  const demandPoints = useMemo(() => getDemandPointsFromCache(cached), [cached]);

  const mandiFulfilment = useMemo(
    () => buildMandiFulfilmentRows(cached, rawRoutes, demandPoints, atRiskMap),
    [cached, rawRoutes, demandPoints, atRiskMap],
  );

  const mandiSummary = useMemo(() => summarizeMandiFulfilment(mandiFulfilment), [mandiFulfilment]);

  const mandiShortageCount = useMemo(
    () => mandiFulfilment.filter((r) => r.shortageKg > 0).length,
    [mandiFulfilment],
  );
  const mandiExcessCount = useMemo(
    () => mandiFulfilment.filter((r) => r.excessKg > 0).length,
    [mandiFulfilment],
  );
  const delayedRouteCount = useMemo(
    () => rawRoutes.filter((r) => {
      const km = r.distance_km != null ? Math.max(0, Math.abs(r.distance_km)) : 0;
      return isTruckDelayed(km, r);
    }).length,
    [rawRoutes],
  );

  const mandiById = useMemo(() => {
    const m = new Map();
    mandiFulfilment.forEach((row) => m.set(row.id, row));
    return m;
  }, [mandiFulfilment]);

  const farmsById = useMemo(() => {
    const farms = Array.isArray(cached?.farms) && cached.farms.length ? cached.farms : DEMO_FARMS;
    return new Map(farms.map((f) => [f.id, f]));
  }, [cached]);

  const supplySuggestions = useMemo(
    () => buildSupplySuggestions(mandiFulfilment, cached, atRiskMap, rawRoutes),
    [mandiFulfilment, cached, atRiskMap, rawRoutes],
  );

  const assignedTruckOptions = useMemo(() => {
    const ids = new Set(routeTruckIds);
    rawRoutes.forEach((r) => { if (r.truck_id) ids.add(r.truck_id); });
    return [...ids].sort();
  }, [routeTruckIds, rawRoutes]);

  const filteredFarmerFarms = useMemo(() => DEMO_FARMS.filter((farm) => {
    const risk = getFarmRiskLevel(farm.id, atRiskMap);
    const truckId = farmTruckMap[farm.id];
    const hours = atRiskMap[farm.id]?.hours_until_spoilage ?? null;
    const crop = (farm.crop_type || '').toLowerCase();

    if (farmerFilters.risk !== 'all' && risk !== farmerFilters.risk) return false;
    if (farmerFilters.crop !== 'all' && !crop.includes(farmerFilters.crop)) return false;
    if (farmerFilters.truck === 'unassigned') {
      if (truckId) return false;
    } else if (farmerFilters.truck !== 'all' && truckId !== farmerFilters.truck) {
      return false;
    }
    if (!matchesSpoilageWindow(hours, farmerFilters.spoilage)) return false;
    return true;
  }), [farmerFilters, atRiskMap, farmTruckMap]);

  const filteredMandiFulfilment = useMemo(() => mandiFulfilment.filter((row) => {
    const q = mandiFilters.search.trim().toLowerCase();
    if (q && !(row.name || '').toLowerCase().includes(q) && !row.id.toLowerCase().includes(q)) {
      return false;
    }
    if (mandiFilters.status !== 'all') {
      const labels = MANDI_STATUS_GROUPS[mandiFilters.status] || [];
      if (!labels.includes(row.statusLabel)) return false;
    }
    if (!matchesCoverageRange(row.fulfilmentPct, mandiFilters.coverage)) return false;
    return true;
  }), [mandiFulfilment, mandiFilters]);

  const transportRows = useMemo(() => DEMO_TRUCKS.map((truck) => {
    const route = rawRoutes.find((r) => r.truck_id === truck.id);
    const farmStops = (route?.stops || []).filter((s) => s.demand_point_id == null && s.label);
    const dpStops = (route?.stops || []).filter((s) => s.demand_point_id != null);
    const totalLoad = farmStops.reduce((sum, s) => {
      const stock = atRiskMap[s.label];
      return sum + (stock?.kg_at_risk ?? 0);
    }, 0);
    const distanceKm = route?.distance_km != null
      ? Math.max(0, Math.abs(route.distance_km))
      : 0;
    const loadPct = route ? Math.min(100, (totalLoad / truck.capacity_kg) * 100) : 0;
    const status = !route ? 'idle' : (isTruckDelayed(distanceKm, route) ? 'delayed' : 'assigned');
    const mandiIds = dpStops.map((s) => s.demand_point_id).filter(Boolean);
    return {
      truck,
      route,
      farmStops,
      dpStops,
      totalLoad,
      distanceKm,
      loadPct,
      status,
      mandiIds,
    };
  }), [rawRoutes, atRiskMap]);

  const filteredTransportRows = useMemo(() => transportRows.filter((row) => {
    if (transportFilters.status !== 'all' && row.status !== transportFilters.status) return false;
    if (transportFilters.mandi !== 'all' && !row.mandiIds.includes(transportFilters.mandi)) {
      return false;
    }
    if (!matchesLoadUtilization(row.loadPct, transportFilters.load)) return false;
    return true;
  }), [transportRows, transportFilters]);

  const mandiDestinationOptions = useMemo(
    () => demandPoints.map((dp) => ({ id: dp.id, name: dp.name || dp.id })),
    [demandPoints],
  );

  const lastRun = cached
    ? { runId: cached.run_id, createdAt: cached.plan?.created_at || new Date().toISOString() }
    : runs?.[runs.length - 1];

  const weatherPanel = useMemo(
    () => resolveWeatherPanel(cached),
    [cached],
  );

  return (
    <>
      <Head><title>Dashboard | AgentFarm</title></Head>
      <DashboardLayout title="Dashboard" subtitle={`Run ${runId?.slice(0, 8) || EM_DASH}`}>
        <OverviewPanel lastRun={lastRun} />

        {cached && activeTab === 'overview' && (
          <div className="mt-6">
            <WeatherRiskPanel data={weatherPanel} />
          </div>
        )}

        {cached ? <KPIGrid kpis={kpis} /> : <EmptyState />}

        {/* ---- Role tabs ---------------------------------------------------------------------------------------------------- */}
        {cached && (
          <>
            {/* Tab pill row */}
            <div className="mt-8 flex gap-2 flex-wrap">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
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

            {/* ---- OVERVIEW tab -------------------------------------------------------------------------------------- */}
            {activeTab === 'overview' && (
              <>
                {/* Waste comparison bar chart */}
                {kpis && (
                  <div className="mt-6">
                    <WasteBarChart kpis={kpis} />
                  </div>
                )}

                <section className="mt-6">
                  <SectionCard
                    title="▸ Optimised Routes"
                    badge={
                      selectedTruckId
                        ? `SHOWING: ${displayTruckId(selectedTruckId)}`
                        : `${routesForMap.length} ROUTES · ${DEMO_MAP_FARMS.length} FARMS · ${DEMO_MAP_MANDIS.length} MANDIS`
                    }
                  >
                    <div className="px-4 pt-4">
                      <RouteFilterBar
                        truckIds={routeTruckIds}
                        selectedTruckId={selectedTruckId}
                        onSelect={setSelectedTruckId}
                      />
                    </div>
                    {selectedTruckId && (
                      <RouteSummaryPanel
                        truckId={selectedTruckId}
                        rawRoutes={rawRoutes}
                        atRiskMap={atRiskMap}
                      />
                    )}
                    <div ref={mapPanelRef}>
                      <MapView
                        farms={DEMO_MAP_FARMS}
                        demandPoints={DEMO_MAP_MANDIS}
                        routes={routesForMap}
                        selectedTruckId={selectedTruckId}
                      />
                    </div>
                  </SectionCard>
                </section>
              </>
            )}

            {/* ---- FARMER tab ------------------------------------------------------------------------------------------ */}
            {activeTab === 'farmer' && (
              <section className="mt-6 space-y-4">
                <TabFilterBar>
                  <FilterSelect
                    label="Risk level"
                    value={farmerFilters.risk}
                    onChange={(risk) => setFarmerFilters((f) => ({ ...f, risk }))}
                    options={[
                      { value: 'all', label: 'All' },
                      { value: 'severe', label: 'Severe' },
                      { value: 'warning', label: 'Warning' },
                      { value: 'normal', label: 'Normal' },
                    ]}
                  />
                  <FilterSelect
                    label="Crop type"
                    value={farmerFilters.crop}
                    onChange={(crop) => setFarmerFilters((f) => ({ ...f, crop }))}
                    options={[
                      { value: 'all', label: 'All' },
                      ...CROP_FILTER_OPTIONS.map((c) => ({ value: c, label: c })),
                    ]}
                  />
                  <FilterSelect
                    label="Assigned truck"
                    value={farmerFilters.truck}
                    onChange={(truck) => setFarmerFilters((f) => ({ ...f, truck }))}
                    options={[
                      { value: 'all', label: 'All' },
                      { value: 'unassigned', label: 'Unassigned' },
                      ...assignedTruckOptions.map((id) => ({ value: id, label: id })),
                    ]}
                  />
                  <FilterSelect
                    label="Spoilage window"
                    value={farmerFilters.spoilage}
                    onChange={(spoilage) => setFarmerFilters((f) => ({ ...f, spoilage }))}
                    options={[
                      { value: 'all', label: 'All' },
                      { value: 'lt24', label: '<24h' },
                      { value: '24-48', label: '24-48h' },
                      { value: '48-72', label: '48-72h' },
                      { value: 'gt72', label: '>72h' },
                    ]}
                  />
                </TabFilterBar>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <SectionCard
                  title="▸ Your Farms at Risk Today"
                  badge={`${filteredFarmerFarms.length} / ${DEMO_FARMS.length} FARMS`}
                >
                  <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
                    {filteredFarmerFarms.length === 0 ? (
                      <p className="px-5 py-6 font-mono text-muted text-[12px]">
                        No farms match the selected filters.
                      </p>
                    ) : filteredFarmerFarms.map((farm) => {
                      const idx = DEMO_FARMS.findIndex((f) => f.id === farm.id);
                      const stock   = atRiskMap[farm.id];
                      const truckId = farmTruckMap[farm.id];
                      const hours   = stock?.hours_until_spoilage ?? null;
                      const kg      = stock?.kg_at_risk ?? farm.typical_yield_kg;
                      const pickupTime = ESTIMATED_PICKUP_TIMES[idx] || '7:00 AM';
                      return (
                        <div key={farm.id} className="px-5 py-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-syne font-bold text-paper flex items-center gap-2" style={{ fontSize: '13px' }}>
                                <span
                                  aria-hidden
                                  style={{ color: 'var(--green-ok)', fontSize: '10px', lineHeight: 1 }}
                                >
                                  ●
                                </span>
                                {farm.name}
                              </p>
                              <p className="font-mono text-muted mt-1" style={{ fontSize: '11px' }}>
                                {kg.toLocaleString()} kg at risk
                                {hours != null ? ` ${MIDDOT} ${Math.round(hours)}h until spoilage` : ''}
                              </p>
                              {truckId && (
                                <p className="font-mono mt-1" style={{ fontSize: '11px', color: 'var(--accent)' }}>
                                  Truck assigned: {displayTruckId(truckId)} {MIDDOT} pickup {pickupTime}
                                </p>
                              )}
                              {!truckId && (
                                <p className="font-mono mt-1" style={{ fontSize: '11px', color: 'var(--red-risk)' }}>
                                  <span aria-hidden>{WARN}</span>
                                  {' '}
                                  No truck assigned yet
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

                <SectionCard
                  title="▸ What To Do Today"
                  badge={`${filteredFarmerFarms.length} ACTIONS`}
                >
                  <div className="px-5 py-4 space-y-4">
                    {filteredFarmerFarms.length === 0 ? (
                      <p className="font-mono text-muted text-[12px]">No farms match the selected filters.</p>
                    ) : filteredFarmerFarms.map((farm) => {
                      const idx = DEMO_FARMS.findIndex((f) => f.id === farm.id);
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
                </div>
              </section>
            )}

            {/* MANDI tab — supply fulfilment dashboard */}
            {activeTab === 'mandi' && (
              <section className="mt-6 space-y-8">
                <MandiSummaryGrid
                  summary={mandiSummary}
                  shortageMandiCount={mandiShortageCount}
                  excessMandiCount={mandiExcessCount}
                />

                <MandiRiskHighlights
                  rows={mandiFulfilment}
                  cached={cached}
                  delayedRouteCount={delayedRouteCount}
                />

                <TabFilterBar>
                  <FilterSelect
                    label="Supply status"
                    value={mandiFilters.status}
                    onChange={(status) => setMandiFilters((f) => ({ ...f, status }))}
                    options={[
                      { value: 'all', label: 'All' },
                      { value: 'shortage', label: 'Shortage' },
                      { value: 'nearly_met', label: 'Nearly Met' },
                      { value: 'supply_met', label: 'Supply Met' },
                      { value: 'excess', label: 'Excess' },
                    ]}
                  />
                  <FilterSelect
                    label="Coverage"
                    value={mandiFilters.coverage}
                    onChange={(coverage) => setMandiFilters((f) => ({ ...f, coverage }))}
                    options={[
                      { value: 'all', label: 'All' },
                      { value: 'lt50', label: '<50%' },
                      { value: '50-80', label: '50-80%' },
                      { value: '80-100', label: '80-100%' },
                      { value: 'gt100', label: '>100%' },
                    ]}
                  />
                  <FilterSearch
                    label="Mandi name"
                    value={mandiFilters.search}
                    onChange={(search) => setMandiFilters((f) => ({ ...f, search }))}
                    placeholder="Search mandis…"
                  />
                </TabFilterBar>

                <SectionCard
                  title="▸ Mandi Fulfilment"
                  badge={`${filteredMandiFulfilment.length} / ${mandiFulfilment.length} MANDIS`}
                >
                  {mandiFulfilment.length === 0 ? (
                    <p className="px-5 py-6 font-mono text-muted text-[12px]">
                      No demand points in this run. Re-run a scenario to refresh plan data.
                    </p>
                  ) : filteredMandiFulfilment.length === 0 ? (
                    <p className="px-5 py-6 font-mono text-muted text-[12px]">
                      No mandis match the selected filters.
                    </p>
                  ) : (
                    <div>
                      {filteredMandiFulfilment.map((row, idx) => (
                        <MandiFulfilmentCard key={row.id} row={row} isFirst={idx === 0} />
                      ))}
                    </div>
                  )}
                </SectionCard>

                {mandiFulfilment.length > 0 && supplySuggestions.length > 0 && (
                  <SectionCard title="▸ Supply Balancing Suggestions">
                    <ul className="px-5 py-4 space-y-3">
                      {supplySuggestions.map((text, i) => (
                        <li
                          key={i}
                          className="font-mono text-paper pl-3"
                          style={{
                            fontSize: '12px',
                            lineHeight: 1.6,
                            borderLeft: '2px solid var(--accent)',
                          }}
                        >
                          {text}
                        </li>
                      ))}
                    </ul>
                  </SectionCard>
                )}
              </section>
            )}


            {/* ---- TRANSPORT tab ------------------------------------------------------------------------------------ */}
            {activeTab === 'transport' && (
              <section className="mt-6 space-y-6">
                <RouteFilterBar
                  truckIds={routeTruckIds}
                  selectedTruckId={selectedTruckId}
                  onSelect={setSelectedTruckId}
                />

                <TabFilterBar>
                  <FilterSelect
                    label="Truck status"
                    value={transportFilters.status}
                    onChange={(status) => setTransportFilters((f) => ({ ...f, status }))}
                    options={[
                      { value: 'all', label: 'All' },
                      { value: 'assigned', label: 'Assigned' },
                      { value: 'idle', label: 'Idle' },
                      { value: 'delayed', label: 'Delayed' },
                    ]}
                  />
                  <FilterSelect
                    label="Destination mandi"
                    value={transportFilters.mandi}
                    onChange={(mandi) => setTransportFilters((f) => ({ ...f, mandi }))}
                    options={[
                      { value: 'all', label: 'All' },
                      ...mandiDestinationOptions.map((dp) => ({
                        value: dp.id,
                        label: dp.name,
                      })),
                    ]}
                  />
                  <FilterSelect
                    label="Load utilization"
                    value={transportFilters.load}
                    onChange={(load) => setTransportFilters((f) => ({ ...f, load }))}
                    options={[
                      { value: 'all', label: 'All' },
                      { value: 'lt50', label: '<50%' },
                      { value: '50-80', label: '50-80%' },
                      { value: '80-100', label: '80-100%' },
                    ]}
                  />
                </TabFilterBar>

                <p
                  className="font-mono text-muted uppercase"
                  style={{ fontSize: '10px', letterSpacing: '0.12em' }}
                >
                  {filteredTransportRows.length} / {DEMO_TRUCKS.length} trucks shown
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">
                  {filteredTransportRows.length === 0 ? (
                    <p
                      className="col-span-full font-mono text-muted text-center py-8"
                      style={{ fontSize: '12px' }}
                    >
                      No trucks match the selected filters.
                    </p>
                  ) : filteredTransportRows.map((row) => {
                    const {
                      truck, route, farmStops, dpStops, totalLoad, distanceKm, loadPct, status,
                    } = row;
                    const farmNames = farmStops.map((s) => {
                      const f = DEMO_FARMS.find((f) => f.id === s.label);
                      return f?.name || s.label;
                    });
                    const dpNames = dpStops.map((s) => {
                      const d = DEMO_DEMAND_POINTS.find((d) => d.id === (s.demand_point_id || s.label));
                      return d?.name || s.demand_point_id || s.label;
                    });
                    return (
                      <TruckCard
                        key={truck.id}
                        truck={truck}
                        route={route}
                        farmNames={farmNames}
                        dpNames={dpNames}
                        totalLoad={totalLoad}
                        distanceKm={distanceKm}
                        loadPct={loadPct}
                        status={status}
                        isSelected={selectedTruckId === truck.id}
                        onSelect={() => handleTruckSelect(truck.id)}
                        atRiskMap={atRiskMap}
                        mandiById={mandiById}
                        farmsById={farmsById}
                        computeETA={computeETA}
                      />
                    );
                  })}
                </div>

                {/* Click-to-highlight hint */}
                <p className="font-mono text-muted text-center" style={{ fontSize: '10px', letterSpacing: '0.12em' }}>
                  {selectedTruckId
                    ? `Showing route for ${displayTruckId(selectedTruckId)} — click card again to deselect`
                    : 'Click a truck card to highlight its route on the map'}
                </p>

                {selectedTruckId && (
                  <RouteSummaryPanel
                    truckId={selectedTruckId}
                    rawRoutes={rawRoutes}
                    atRiskMap={atRiskMap}
                  />
                )}

                <SectionCard
                  title="▸ Route Map"
                  badge={selectedTruckId ? `SHOWING: ${displayTruckId(selectedTruckId)}` : `${routesForMap.length} ACTIVE ROUTES`}
                >
                  <div ref={mapPanelRef}>
                    <MapView
                      farms={DEMO_MAP_FARMS}
                      demandPoints={DEMO_MAP_MANDIS}
                      routes={routesForMap}
                      selectedTruckId={selectedTruckId}
                    />
                  </div>
                </SectionCard>
              </section>
            )}
          </>
        )}

        {/* ---- Recent Runs ------------------------------------------------------------------------------------------------ */}
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

/* ---- Sub-components -------------------------------------------------------------------------------------------------------------- */

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
      to populate KPIs and routes.
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
          <span>{supplyKg ? supplyKg.toLocaleString() : EM_DASH} kg</span>
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

/* ---- Waste Comparison Bar Chart -------------------------------------------------------------------------------------- */
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
          {`${SECTION} Waste Reduction ${EM_DASH} Naive vs Optimised`}
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

/* ── Tab filter UI ──────────────────────────────────────────────────────── */

function TabFilterBar({ children }) {
  return (
    <div
      className="flex flex-wrap gap-4 items-end p-4"
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: '4px',
      }}
    >
      {children}
    </div>
  );
}

function FilterSelect({ label, value, onChange, options }) {
  return (
    <label className="flex flex-col gap-1 min-w-[140px]">
      <span
        className="font-mono text-muted uppercase"
        style={{ fontSize: '9px', letterSpacing: '0.12em' }}
      >
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="font-mono px-2 py-1.5 outline-none"
        style={{
          fontSize: '11px',
          color: 'var(--text)',
          background: 'var(--bg)',
          border: '1px solid var(--border)',
          borderRadius: '2px',
          cursor: 'pointer',
        }}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </label>
  );
}

function FilterSearch({ label, value, onChange, placeholder }) {
  return (
    <label className="flex flex-col gap-1 flex-1 min-w-[180px]">
      <span
        className="font-mono text-muted uppercase"
        style={{ fontSize: '9px', letterSpacing: '0.12em' }}
      >
        {label}
      </span>
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="font-mono px-2 py-1.5 outline-none w-full"
        style={{
          fontSize: '11px',
          color: 'var(--text)',
          background: 'var(--bg)',
          border: '1px solid var(--border)',
          borderRadius: '2px',
        }}
      />
    </label>
  );
}

/* ── Route filter & summary ─────────────────────────────────────────────── */

function RouteFilterBar({ truckIds, selectedTruckId, onSelect }) {
  if (!truckIds?.length) return null;
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filter routes by truck">
      <RouteFilterButton
        label="All routes"
        active={selectedTruckId === null}
        onClick={() => onSelect(null)}
      />
      {truckIds.map((id) => (
        <RouteFilterButton
          key={id}
          label={displayTruckId(id)}
          active={selectedTruckId === id}
          onClick={() => onSelect(selectedTruckId === id ? null : id)}
        />
      ))}
    </div>
  );
}

function RouteFilterButton({ label, active, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="px-3 py-1.5 font-mono uppercase tracking-wider transition"
      style={{
        fontSize: '10px',
        letterSpacing: '0.12em',
        borderRadius: '2px',
        border: active ? '1px solid var(--accent)' : '1px solid var(--border)',
        background: active ? 'rgba(245,166,35,0.12)' : 'transparent',
        color: active ? 'var(--accent)' : 'var(--muted)',
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  );
}

function RouteSummaryPanel({ truckId, rawRoutes, atRiskMap }) {
  const route = rawRoutes.find((r) => r.truck_id === truckId);
  const truck = DEMO_TRUCKS.find((t) => t.id === truckId);
  if (!route) return null;

  const stops = [...(route.stops || [])].sort(
    (a, b) => (a.sequence ?? 0) - (b.sequence ?? 0),
  );
  const farmStops = stops.filter((s) => s.demand_point_id == null && s.label);
  const totalLoad = farmStops.reduce((sum, s) => {
    const stock = atRiskMap[s.label];
    return sum + (stock?.kg_at_risk ?? 0);
  }, 0);
  const distanceKm = Math.max(0, Math.abs(route.distance_km ?? 0));
  const etaTime = computeETA(distanceKm);
  const capacityKg = truck?.capacity_kg ?? null;

  const stopLabels = stops.map((s, idx) => {
    if (s.demand_point_id != null) {
      const dp = DEMO_DEMAND_POINTS.find((d) => d.id === s.demand_point_id);
      return `${idx + 1}. ${dp?.name || s.demand_point_id}`;
    }
    const farm = DEMO_FARMS.find((f) => f.id === s.label);
    return `${idx + 1}. ${farm?.name || s.label}`;
  });

  return (
    <div
      className="mx-4 mb-4 px-4 py-4"
      style={{
        border: '1px solid var(--accent)',
        borderRadius: '4px',
        background: 'rgba(245,166,35,0.05)',
      }}
    >
      <p className="font-syne font-bold uppercase text-paper tracking-wider" style={{ fontSize: '13px' }}>
        Route summary — {displayTruckId(truckId)}
      </p>
      <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryStat label="Capacity" value={capacityKg != null ? `${capacityKg.toLocaleString()} kg` : '—'} />
        <SummaryStat label="Load" value={`${Math.round(totalLoad).toLocaleString()} kg`} />
        <SummaryStat label="Distance" value={distanceKm > 0 ? `~${distanceKm.toFixed(0)} km` : '—'} />
        <SummaryStat label="ETA" value={etaTime} />
      </div>
      <p className="font-mono text-muted mt-3 mb-1" style={{ fontSize: '10px', letterSpacing: '0.1em' }}>
        STOPS (IN ORDER)
      </p>
      <ol className="font-mono text-paper m-0 pl-4" style={{ fontSize: '11px', lineHeight: 1.7 }}>
        {stopLabels.map((label) => (
          <li key={label}>{label}</li>
        ))}
      </ol>
    </div>
  );
}

function SummaryStat({ label, value }) {
  return (
    <div>
      <p className="font-mono text-muted uppercase" style={{ fontSize: '9px', letterSpacing: '0.12em' }}>
        {label}
      </p>
      <p className="font-syne font-bold text-paper mt-0.5" style={{ fontSize: '13px' }}>
        {value}
      </p>
    </div>
  );
}


/**
 * Estimate arrival time from distance.
 * Assumes truck departs depot at startHour (default 6:00 AM) at avgSpeedKmh (default 40 km/h).
 * Returns a formatted time string like "9:45 AM", or "TBD" when distance is unavailable.
 */
function computeETA(distanceKm, startHour = 6, avgSpeedKmh = 40) {
  if (!distanceKm || distanceKm <= 0) return 'TBD';
  const totalMin   = Math.round((distanceKm / avgSpeedKmh) * 60);
  const etaTotalMin = startHour * 60 + totalMin;
  const h   = Math.floor(etaTotalMin / 60) % 24;
  const m   = etaTotalMin % 60;
  const period = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 || 12;
  return `${h12}:${m.toString().padStart(2, '0')} ${period}`;
}

function LegendDot({ color, label }) {
  return (
    <div className="flex items-center gap-2">
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }} />
      <span className="font-mono text-muted" style={{ fontSize: '11px' }}>{label}</span>
    </div>
  );
}
