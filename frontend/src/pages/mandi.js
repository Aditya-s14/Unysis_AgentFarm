import Head from 'next/head';
import { useMemo, useState } from 'react';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import MandiFulfilmentCard from '@/components/Mandi/MandiFulfilmentCard';
import DeliveryOutcomeModal from '@/components/Mandi/DeliveryOutcomeModal';
import withAuth from '@/components/withAuth';
import { useAppContext } from '@/context/AppContext';
import useOutcomeLog from '@/hooks/useOutcomeLog';
import { useCachedRunResponse } from '@/hooks/useRuns';
import { DEMO_DEMAND_POINTS, DEMO_FARMS } from '@/utils/demoFixtures';
import { buildMandiFulfilmentRows, getDemandPointsFromCache } from '@/utils/mandiFulfilment';
import { etaFromMinutes } from '@/utils/eta';

function MandiPage() {
  const { user } = useAppContext();
  const mandiId = user?.entityId;

  const cached = useCachedRunResponse();
  const runId = cached?.run_id || null;

  const rawRoutes = useMemo(() => cached?.plan?.route_plan?.routes || [], [cached]);

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

  const mandiInfo = DEMO_DEMAND_POINTS.find((d) => d.id === mandiId);
  const fulfilRow = mandiFulfilment.find((r) => r.id === mandiId);

  // FPO sees all mandis overview
  if (user?.role === 'fpo') {
    return (
      <>
        <Head><title>All Mandis | AgentFarm</title></Head>
        <DashboardLayout title="Mandi Overview" subtitle={`${DEMO_DEMAND_POINTS.length} demand points`}>
          <div className="space-y-3">
            {DEMO_DEMAND_POINTS.map((dp) => {
              const row = mandiFulfilment.find((r) => r.id === dp.id);
              const trucks = rawRoutes.filter((r) =>
                (r.stops || []).some((s) => s.demand_point_id === dp.id)
              );
              return (
                <div key={dp.id} className="p-4 flex items-center justify-between"
                  style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}>
                  <div>
                    <p className="font-syne font-bold text-[13px]" style={{ color: 'var(--text)' }}>{dp.name}</p>
                    <p className="font-mono text-[11px] mt-0.5" style={{ color: 'var(--muted)' }}>
                      {dp.point_type?.toUpperCase()} · {dp.base_demand_per_day?.toLocaleString()} kg/day
                      {trucks.length > 0 ? ` · ${trucks.length} truck(s) incoming` : ' · No trucks routed'}
                    </p>
                  </div>
                  {row ? (
                    <span className="font-mono text-[11px] px-2 py-0.5"
                      style={{ color: row.statusColor, border: `1px solid ${row.statusColor}`, borderRadius: '2px' }}>
                      {row.fulfilmentPct?.toFixed(0)}% fulfilled
                    </span>
                  ) : (
                    <span className="font-mono text-[11px]" style={{ color: 'var(--muted)' }}>No data</span>
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
        <title>{mandiInfo?.name || mandiId} | Mandi Dashboard</title>
      </Head>
      <DashboardLayout
        title={mandiInfo?.name || mandiId}
        subtitle={mandiInfo ? `${mandiInfo.point_type?.toUpperCase()} · ${mandiInfo.base_demand_per_day?.toLocaleString()} kg/day` : 'Mandi Dashboard'}
      >
        <MandiContent
          mandiId={mandiId}
          runId={runId}
          cached={cached}
          mandiInfo={mandiInfo}
          fulfilRow={fulfilRow}
          rawRoutes={rawRoutes}
        />
      </DashboardLayout>
    </>
  );
}

function MandiContent({ mandiId, runId, cached, mandiInfo, fulfilRow, rawRoutes }) {
  const [outcomeModalMandi, setOutcomeModalMandi] = useState(null);
  const {
    logMandiOutcome,
    logging: outcomeLogging,
    isLogged: isMandiOutcomeLogged,
  } = useOutcomeLog(runId);

  const incomingTrucks = useMemo(() => {
    const trucks = [];
    rawRoutes.forEach((route) => {
      const stop = (route.stops || []).find((s) => s.demand_point_id === mandiId);
      if (stop) {
        trucks.push({
          truck_id: route.truck_id,
          eta: etaFromMinutes(stop.eta_minutes_from_start),
          eta_minutes: stop.eta_minutes_from_start,
          load_kg: stop.load_kg,
          distance_km: route.distance_km,
        });
      }
    });
    return trucks.sort((a, b) => (a.eta_minutes ?? 9999) - (b.eta_minutes ?? 9999));
  }, [rawRoutes, mandiId]);

  const pct = fulfilRow?.fulfilmentPct ?? 0;
  const statusColor = fulfilRow?.statusColor || 'var(--muted)';

  return (
    <div className="space-y-6">
      {fulfilRow && (
        <div
          style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)', overflow: 'hidden' }}
        >
          <MandiFulfilmentCard
            row={fulfilRow}
            isFirst
            canLogOutcome={(fulfilRow.incomingSupply ?? 0) > 0}
            isLogged={isMandiOutcomeLogged(mandiId)}
            onConfirmDelivery={setOutcomeModalMandi}
          />
        </div>
      )}

      {outcomeModalMandi && (
        <DeliveryOutcomeModal
          mandiRow={outcomeModalMandi}
          cached={cached}
          rawRoutes={rawRoutes}
          farms={Array.isArray(cached?.farms) && cached.farms.length ? cached.farms : DEMO_FARMS}
          loading={outcomeLogging}
          onClose={() => setOutcomeModalMandi(null)}
          onSubmit={(actualOverrides) => logMandiOutcome({
            mandiRow: outcomeModalMandi,
            cached,
            rawRoutes,
            farms: Array.isArray(cached?.farms) && cached.farms.length ? cached.farms : DEMO_FARMS,
            actualOverrides,
          })}
        />
      )}

      {/* Stock vs Demand */}
      {fulfilRow ? (
        <div
          className="p-5"
          style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
        >
          <div className="flex items-baseline justify-between mb-3">
            <p className="font-mono uppercase text-[10px] tracking-widest" style={{ color: 'var(--muted)' }}>
              Supply Fulfilment
            </p>
            <span
              className="font-mono uppercase text-[10px] tracking-wider px-2 py-0.5"
              style={{ border: `1px solid ${statusColor}`, color: statusColor, borderRadius: '2px' }}
            >
              {fulfilRow.statusLabel}
            </span>
          </div>

          <div className="flex items-end gap-6 mb-4">
            <div>
              <p className="font-syne font-bold" style={{ fontSize: '28px', color: 'var(--text)' }}>
                {pct.toFixed(0)}%
              </p>
              <p className="font-mono text-[11px]" style={{ color: 'var(--muted)' }}>fulfilment</p>
            </div>
            <div>
              <p className="font-mono text-[13px]" style={{ color: 'var(--text)' }}>
                {fulfilRow.incomingKg?.toLocaleString()} kg incoming
              </p>
              <p className="font-mono text-[11px]" style={{ color: 'var(--muted)' }}>
                of {fulfilRow.expectedDemand?.toLocaleString()} kg demand
              </p>
            </div>
          </div>

          <div
            className="h-3 rounded-full overflow-hidden"
            style={{ background: 'var(--border)' }}
          >
            <div
              className="h-full transition-all duration-500"
              style={{ width: `${Math.min(100, pct)}%`, background: statusColor }}
            />
          </div>

          {fulfilRow.shortageKg > 0 && (
            <p className="font-mono mt-2 text-[11px]" style={{ color: 'var(--red-risk)' }}>
              Shortage: {fulfilRow.shortageKg?.toLocaleString()} kg
            </p>
          )}
          {fulfilRow.excessKg > 0 && (
            <p className="font-mono mt-2 text-[11px]" style={{ color: 'var(--green-ok)' }}>
              Surplus: {fulfilRow.excessKg?.toLocaleString()} kg
            </p>
          )}
        </div>
      ) : (
        <div
          className="p-5"
          style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
        >
          <p className="font-mono text-muted text-[12px]">No supply data. Run a scenario first.</p>
        </div>
      )}

      {/* Incoming Trucks */}
      <div
        className="p-5"
        style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
      >
        <p className="font-mono uppercase text-[10px] tracking-widest mb-3" style={{ color: 'var(--muted)' }}>
          Incoming Trucks
        </p>
        {incomingTrucks.length === 0 ? (
          <p className="font-mono text-muted text-[12px]">No trucks routed to this mandi.</p>
        ) : (
          <div className="space-y-3">
            {incomingTrucks.map((t, i) => (
              <div
                key={t.truck_id || i}
                className="flex items-center justify-between"
                style={{ borderBottom: i < incomingTrucks.length - 1 ? '1px solid var(--border)' : 'none', paddingBottom: i < incomingTrucks.length - 1 ? '12px' : 0 }}
              >
                <div>
                  <p className="font-syne font-bold text-paper text-[13px]">{t.truck_id}</p>
                  {t.load_kg != null && (
                    <p className="font-mono text-[11px] mt-0.5" style={{ color: 'var(--muted)' }}>
                      ~{Math.round(t.load_kg).toLocaleString()} kg
                    </p>
                  )}
                </div>
                <div className="text-right">
                  {t.eta ? (
                    <p className="font-mono font-bold text-[13px]" style={{ color: 'var(--accent)' }}>
                      ETA {t.eta}
                    </p>
                  ) : (
                    <p className="font-mono text-[12px]" style={{ color: 'var(--muted)' }}>ETA TBD</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Mandi info */}
      {mandiInfo && (
        <div
          className="p-5"
          style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
        >
          <p className="font-mono uppercase text-[10px] tracking-widest mb-3" style={{ color: 'var(--muted)' }}>
            Mandi Details
          </p>
          <div className="grid grid-cols-2 gap-3">
            {[
              ['Type', mandiInfo.point_type?.toUpperCase()],
              ['Base demand', `${mandiInfo.base_demand_per_day?.toLocaleString()} kg/day`],
              ['Location', `${mandiInfo.lat?.toFixed(4)}, ${mandiInfo.lng?.toFixed(4)}`],
              ['Run ID', runId ? runId.slice(0, 12) + '...' : '-'],
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
  );
}

export default withAuth(MandiPage, ['mandi', 'fpo']);

