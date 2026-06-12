import Head from 'next/head';
import { useCallback, useMemo, useState } from 'react';
// useRouter removed â€” entity_id comes from AuthContext, not URL param
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import { postMandiConfirm } from '@/api/client';
import withAuth from '@/components/withAuth';
import { useAppContext } from '@/context/AppContext';
import { useCachedRunResponse } from '@/hooks/useRuns';
import { DEMO_DEMAND_POINTS } from '@/utils/demoFixtures';
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
          mandiInfo={mandiInfo}
          fulfilRow={fulfilRow}
          rawRoutes={rawRoutes}
        />
      </DashboardLayout>
    </>
  );
}

function MandiContent({ mandiId, runId, mandiInfo, fulfilRow, rawRoutes }) {
  const confirmKey = runId && mandiId ? `mandi_confirmed:${runId}:${mandiId}` : null;
  const [confirmed, setConfirmed] = useState(() => {
    if (typeof window === 'undefined' || !confirmKey) return false;
    return localStorage.getItem(confirmKey) === '1';
  });
  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState(null);

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

  const handleConfirm = useCallback(async () => {
    if (!runId) {
      setConfirmError('No active run. Run a scenario first.');
      return;
    }
    setConfirming(true);
    setConfirmError(null);
    try {
      const totalKg = fulfilRow?.incomingSupply ?? 0;
      const deliveryHours = incomingTrucks[0]?.eta_minutes != null
        ? incomingTrucks[0].eta_minutes / 60
        : 0;
      await postMandiConfirm(runId, mandiId, {
        demand_actual: totalKg,
        delivery_time_actual_hours: deliveryHours,
        crop_type: null,
      });
      setConfirmed(true);
      if (confirmKey) localStorage.setItem(confirmKey, '1');
    } catch {
      setConfirmError('Confirmation failed. Please try again.');
    } finally {
      setConfirming(false);
    }
  }, [runId, mandiId, fulfilRow, incomingTrucks]);

  const pct = fulfilRow?.fulfilmentPct ?? 0;
  const statusColor = fulfilRow?.statusColor || 'var(--muted)';

  return (
    <div className="space-y-6">
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

      {/* Arrival Confirm */}
      <div
        className="p-5"
        style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
      >
        <p className="font-mono uppercase text-[10px] tracking-widest mb-3" style={{ color: 'var(--muted)' }}>
          Confirm Delivery Arrival
        </p>

        {confirmed ? (
          <div className="flex items-center gap-3">
            <span style={{ color: 'var(--green-ok)', fontSize: '20px' }}>&#10003;</span>
            <p className="font-syne font-bold text-[14px]" style={{ color: 'var(--green-ok)' }}>
              Arrival confirmed. Outcome logged for learning loop.
            </p>
          </div>
        ) : (
          <>
            <p className="font-mono text-[12px] mb-4" style={{ color: 'var(--muted)' }}>
              Once trucks arrive and unload, confirm here. This records{' '}
              <strong style={{ color: 'var(--text)' }}>demand_actual</strong> and{' '}
              <strong style={{ color: 'var(--text)' }}>delivery_time_actual_hours</strong> to the Tier-2 learning loop.
            </p>

            <button
              type="button"
              onClick={handleConfirm}
              disabled={confirming}
              className="px-6 py-2.5 font-mono uppercase tracking-wider transition-all"
              style={{
                fontSize: '11px',
                border: '1px solid var(--green-ok)',
                borderRadius: '2px',
                background: 'rgba(76,175,80,0.08)',
                color: 'var(--green-ok)',
                cursor: confirming ? 'not-allowed' : 'pointer',
                opacity: confirming ? 0.6 : 1,
              }}
            >
              {confirming ? 'Confirming...' : 'Confirm Arrival'}
            </button>

            {confirmError && (
              <p className="font-mono mt-2 text-[11px]" style={{ color: 'var(--danger)' }}>{confirmError}</p>
            )}
          </>
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

