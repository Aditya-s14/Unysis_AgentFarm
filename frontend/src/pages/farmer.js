import Head from 'next/head';
import { useMemo } from 'react';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import CropReadyToggle from '@/components/Farmer/CropReadyToggle';
import WeatherForecastStrip from '@/components/Farmer/WeatherForecastStrip';
import TruckETACard from '@/components/Farmer/TruckETACard';
import ArrivalConfirmButton from '@/components/Farmer/ArrivalConfirmButton';
import PriceDiscoveryBoard from '@/components/Farmer/PriceDiscoveryBoard';
import FarmEconomicsPanel from '@/components/Farmer/FarmEconomicsPanel';
import withAuth from '@/components/withAuth';
import { useAppContext } from '@/context/AppContext';
import { useCachedRunResponse } from '@/hooks/useRuns';
import { getMarketCommitmentsForApi } from '@/hooks/useMarketOffers';
import { DEMO_FARMS } from '@/utils/demoFixtures';
import { resolveWeatherPanel } from '@/utils/weatherSummary';

function FarmerPage() {
  const { user } = useAppContext();
  const farmId = user?.entityId;

  const cached = useCachedRunResponse();
  const runId = cached?.run_id || null;

  const farm = useMemo(
    () => DEMO_FARMS.find((f) => f.id === farmId) || null,
    [farmId],
  );

  const rawRoutes = useMemo(
    () => cached?.plan?.route_plan?.routes || [],
    [cached],
  );

  const weatherPanel = useMemo(() => resolveWeatherPanel(cached), [cached]);

  const atRiskStock = useMemo(() => {
    const m = {};
    (cached?.at_risk_stock || []).forEach((s) => { m[s.farm_id] = s; });
    return m;
  }, [cached]);

  const stock = atRiskStock[farmId];

  const guaranteedFarmIds = useMemo(() => {
    const commitments = getMarketCommitmentsForApi();
    return new Set(commitments.map((c) => c.farm_id));
  }, [cached, runId]);

  if (user?.role === 'fpo') {
    return (
      <>
        <Head><title>All Farms | AgentFarm</title></Head>
        <DashboardLayout title="Farmer Overview" subtitle={`${DEMO_FARMS.length} farms`}>
          <div className="space-y-3">
            {DEMO_FARMS.map((f) => {
              const s = atRiskStock[f.id];
              const route = rawRoutes.find((r) => (r.stops || []).some((st) => st.label === f.id));
              const guaranteed = guaranteedFarmIds.has(f.id);
              return (
                <div key={f.id} className="p-4 flex items-center justify-between"
                  style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}>
                  <div>
                    <p className="font-syne font-bold text-[13px] flex items-center gap-2 flex-wrap" style={{ color: 'var(--text)' }}>
                      {f.name}
                      {guaranteed && (
                        <span
                          className="font-mono uppercase"
                          style={{
                            fontSize: '9px',
                            letterSpacing: '0.12em',
                            padding: '2px 8px',
                            border: '1px solid var(--accent)',
                            color: 'var(--accent)',
                            borderRadius: '2px',
                          }}
                        >
                          GUARANTEED
                        </span>
                      )}
                    </p>
                    <p className="font-mono text-[11px] mt-0.5" style={{ color: 'var(--muted)' }}>
                      {f.crop_type} &middot; {f.acreage} acres
                      {route ? ` · Truck ${route.truck_id}` : ' · No truck assigned'}
                    </p>
                  </div>
                  {s ? (
                    <span className="font-mono text-[11px] px-2 py-0.5" style={{ color: 'var(--red-risk)', border: '1px solid var(--red-risk)', borderRadius: '2px' }}>
                      {s.kg_at_risk?.toLocaleString()} kg at risk
                    </span>
                  ) : (
                    <span className="font-mono text-[11px]" style={{ color: 'var(--green-ok)' }}>OK</span>
                  )}
                </div>
              );
            })}
          </div>
        </DashboardLayout>
      </>
    );
  }

  return (
    <>
      <Head>
        <title>{farm?.name || farmId} | Farmer Dashboard</title>
      </Head>
      <DashboardLayout
        title={farm?.name || farmId}
        subtitle={farm ? `${farm.crop_type} · ${farm.acreage} acres` : 'Farmer Dashboard'}
      >
        <div className="space-y-6">
          <PriceDiscoveryBoard farmId={farmId} />

          {stock && (
            <div
              className="px-5 py-3 flex items-center gap-4"
              style={{
                border: '1px solid var(--red-risk)',
                borderRadius: '4px',
                background: 'rgba(220,50,50,0.05)',
              }}
            >
              <span style={{ color: 'var(--red-risk)', fontSize: '18px' }}>&#9888;</span>
              <div>
                <p className="font-syne font-bold text-[13px]" style={{ color: 'var(--red-risk)' }}>
                  {stock.kg_at_risk?.toLocaleString()} kg at risk
                </p>
                {stock.hours_until_spoilage != null && (
                  <p className="font-mono text-[11px] mt-0.5" style={{ color: 'var(--muted)' }}>
                    {Math.round(stock.hours_until_spoilage)}h until spoilage &middot; act fast to avoid losses
                  </p>
                )}
              </div>
            </div>
          )}

          <CropReadyToggle farmId={farmId} />
          <TruckETACard farmId={farmId} rawRoutes={rawRoutes} />
          <ArrivalConfirmButton runId={runId} farmId={farmId} />
          <WeatherForecastStrip weatherPanel={weatherPanel} />
          <FarmEconomicsPanel farmId={farmId} />

          {farm && (
            <div
              className="p-5"
              style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
            >
              <p className="font-mono uppercase text-[10px] tracking-widest mb-3 flex items-center gap-2 flex-wrap" style={{ color: 'var(--muted)' }}>
                Farm Details
                {guaranteedFarmIds.has(farmId) && (
                  <span
                    className="font-mono uppercase"
                    style={{
                      fontSize: '9px',
                      letterSpacing: '0.12em',
                      padding: '2px 8px',
                      border: '1px solid var(--accent)',
                      color: 'var(--accent)',
                      borderRadius: '2px',
                    }}
                  >
                    GUARANTEED
                  </span>
                )}
              </p>
              <div className="grid grid-cols-2 gap-3">
                {[
                  ['Crop', farm.crop_type],
                  ['Acreage', `${farm.acreage} acres`],
                  ['Typical yield', `${farm.typical_yield_kg?.toLocaleString()} kg`],
                  ['Harvest window', `${farm.harvest_window_start} to ${farm.harvest_window_end}`],
                  ['Phone', farm.phone || 'N/A'],
                  ['Run ID', runId ? runId.slice(0, 12) + '...' : 'N/A'],
                ].map(([label, value]) => (
                  <div key={label}>
                    <p className="font-mono text-[10px] uppercase tracking-wider mb-0.5" style={{ color: 'var(--muted)' }}>
                      {label}
                    </p>
                    <p className="font-mono text-[12px]" style={{ color: 'var(--text)' }}>{value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </DashboardLayout>
    </>
  );
}

export default withAuth(FarmerPage, ['farmer', 'fpo']);
