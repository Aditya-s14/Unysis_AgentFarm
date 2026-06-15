import Head from 'next/head';
import { useRouter } from 'next/router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { postTruckPosition, getRun } from '@/api/client';
import BreakdownReportModal from '@/components/Transport/BreakdownReportModal';
import AlternateStopsPanel from '@/components/Transport/AlternateStopsPanel';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import withAuth from '@/components/withAuth';
import { useAppContext } from '@/context/AppContext';
import { formatApiError } from '@/utils/api';
import { DEMO_TRUCKS, DEMO_FARMS, DEMO_DEMAND_POINTS } from '@/utils/demoFixtures';
import { displayTruckId } from '@/utils/truckDisplay';
import { etaFromMinutes, minutesUntilETA } from '@/utils/eta';

const SEND_INTERVAL_MS = 30000;

const RISK_COLORS = { severe: 'var(--red-risk)', warning: 'var(--harvest-gold)', normal: 'var(--green-ok)' };

const CARD = {
  border: '1px solid var(--border)',
  borderRadius: '4px',
  background: 'var(--bg-card)',
};

function getRiskFromStock(stock) {
  if (!stock) return 'normal';
  const hours = stock.hours_until_spoilage;
  if (hours != null && hours < 24) return 'severe';
  if (hours != null && hours < 48) return 'warning';
  return 'normal';
}

function DriverDashboardPage() {
  const router = useRouter();
  const { runId, truckId } = router.query;
  const { user } = useAppContext();

  useEffect(() => {
    if (user && runId && truckId && truckId !== user.entityId) {
      router.replace(`/driver/${runId}/${user.entityId}`);
    }
  }, [user, runId, truckId, router]);

  const [status, setStatus] = useState('idle');
  const [lastPosition, setLastPosition] = useState(null);
  const [gpsError, setGpsError] = useState(null);
  const [planData, setPlanData] = useState(null);
  const [showBreakdown, setShowBreakdown] = useState(false);
  const watchIdRef = useRef(null);
  const intervalRef = useRef(null);

  const sendPosition = useCallback(async (coords) => {
    if (!runId || !truckId) return;
    try {
      const resp = await postTruckPosition(runId, truckId, {
        lat: coords.latitude,
        lng: coords.longitude,
        accuracy_m: coords.accuracy,
        reported_by: 'driver',
      });
      setLastPosition(resp.position);
      setStatus(resp.alert_triggered ? 'alert' : (resp.position?.on_route ? 'on_route' : 'off_route'));
      setGpsError(null);
    } catch (err) {
      setGpsError(formatApiError(err));
      setStatus('error');
    }
  }, [runId, truckId]);

  useEffect(() => {
    if (!runId || !truckId || typeof window === 'undefined') return undefined;
    if (!navigator.geolocation) {
      setGpsError('Geolocation not supported on this device');
      return undefined;
    }

    const onPosition = (pos) => sendPosition(pos.coords);
    const onError = (err) => { setGpsError(err.message || 'Geolocation error'); setStatus('error'); };

    watchIdRef.current = navigator.geolocation.watchPosition(onPosition, onError, {
      enableHighAccuracy: true, maximumAge: 10000, timeout: 20000,
    });
    intervalRef.current = setInterval(() => {
      navigator.geolocation.getCurrentPosition(onPosition, onError, {
        enableHighAccuracy: true, timeout: 15000,
      });
    }, SEND_INTERVAL_MS);
    setStatus('tracking');

    return () => {
      if (watchIdRef.current != null) navigator.geolocation.clearWatch(watchIdRef.current);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [runId, truckId, sendPosition]);

  useEffect(() => {
    if (!runId) return;
    getRun(runId).then(setPlanData).catch(() => {});
  }, [runId]);

  const myRoute = planData?.route_plan?.routes?.find((r) => r.truck_id === truckId);
  const atRiskMap = {};
  (planData?.at_risk_stock || []).forEach((s) => { atRiskMap[s.farm_id] = s; });

  const sortedStops = (myRoute?.stops || [])
    .slice()
    .sort((a, b) => (a.sequence ?? 0) - (b.sequence ?? 0));

  const farmStops = sortedStops.filter((s) => !s.demand_point_id);

  const truckLabel = truckId ? displayTruckId(String(truckId)) : 'Truck';

  const nearbyTrucks = DEMO_TRUCKS.filter(
    (t) => t.id !== truckId && t.driver_phone,
  );

  const statusColors = {
    on_route: 'var(--green-ok)',
    alert: 'var(--red-risk)',
    off_route: 'var(--harvest-gold)',
    error: 'var(--red-risk)',
    tracking: 'var(--green-ok)',
    idle: '#6B7280',
  };

  const stopCount = sortedStops.length;

  return (
    <>
      <Head><title>Driver — {truckLabel}</title></Head>
      <DashboardLayout
        title={truckLabel}
        subtitle={stopCount > 0 ? `${stopCount} stops · Run ${String(runId || '').slice(0, 8)}…` : 'Driver route'}
      >
        <div className="space-y-6 max-w-2xl">
          {/* GPS status */}
          <div className="p-5" style={CARD}>
            <div className="flex items-center justify-between mb-3">
              <p className="font-mono uppercase text-[10px] tracking-widest m-0" style={{ color: 'var(--muted)' }}>
                GPS tracking
              </p>
              <div className="flex items-center gap-2">
                <span className="dot-live" style={{ background: statusColors[status] || '#6B7280' }} />
                <span
                  className="font-mono uppercase tracking-wider"
                  style={{ fontSize: '10px', color: statusColors[status] || '#6B7280' }}
                >
                  {(status || 'idle').replace('_', ' ')}
                </span>
              </div>
            </div>
            <p className="font-mono text-[11px] mb-2" style={{ color: 'var(--text-tertiary)' }}>
              Posting location every 30 seconds
            </p>
            {lastPosition ? (
              <>
                <p className="font-mono text-[13px]" style={{ color: 'var(--navy)' }}>
                  {lastPosition.lat.toFixed(5)}, {lastPosition.lng.toFixed(5)}
                </p>
                <p className="font-mono text-[11px] mt-1" style={{ color: 'var(--muted)' }}>
                  Deviation: {lastPosition.deviation_km?.toFixed?.(1)} km
                </p>
              </>
            ) : (
              <p className="font-mono text-[12px]" style={{ color: 'var(--muted)' }}>Waiting for GPS fix…</p>
            )}
            {gpsError && (
              <p className="font-mono text-[11px] mt-2" style={{ color: 'var(--danger)' }}>{gpsError}</p>
            )}
          </div>

          {/* Route stops */}
          {sortedStops.length > 0 && (
            <div style={CARD}>
              <p className="font-mono uppercase text-[10px] tracking-widest px-5 pt-5 pb-3" style={{ color: 'var(--muted)' }}>
                Route stops ({sortedStops.length})
              </p>
              <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
                {sortedStops.map((stop, i) => {
                  const isMandi = Boolean(stop.demand_point_id);
                  const farmId = !isMandi ? (stop.farm_id || stop.label) : null;
                  const dpId = isMandi ? (stop.demand_point_id) : null;
                  const stock = farmId ? atRiskMap[farmId] : null;
                  const risk = getRiskFromStock(stock);
                  const eta = etaFromMinutes(stop.eta_minutes_from_start);
                  const minsLeft = minutesUntilETA(stop.eta_minutes_from_start);
                  const farm = farmId ? DEMO_FARMS.find((f) => f.id === farmId) : null;
                  const dp = dpId ? DEMO_DEMAND_POINTS.find((d) => d.id === dpId) : null;
                  const lat = farm?.lat ?? dp?.lat;
                  const lng = farm?.lng ?? dp?.lng;
                  const mapsUrl = lat != null && lng != null
                    ? `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
                    : null;
                  const displayName = isMandi
                    ? (dp?.name || stop.label || stop.demand_point_id)
                    : (farm?.name || stop.label || `Stop ${i + 1}`);

                  const rowBg = !isMandi && risk === 'severe'
                    ? 'rgba(231, 76, 60, 0.05)'
                    : !isMandi && risk === 'warning'
                      ? 'rgba(244, 182, 62, 0.06)'
                      : 'transparent';

                  return (
                    <div key={i} className="px-5 py-4" style={{ background: rowBg }}>
                      <div className="flex items-start gap-3">
                        <div
                          className="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center mt-0.5"
                          style={{
                            background: isMandi ? 'var(--forest-mid)' : RISK_COLORS[risk],
                            fontSize: '10px',
                            color: '#fff',
                            fontWeight: 700,
                            fontFamily: "'IBM Plex Sans', sans-serif",
                          }}
                        >
                          {i + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p
                            className="font-syne font-bold text-[13px]"
                            style={{ color: isMandi ? 'var(--forest-mid)' : 'var(--navy)' }}
                          >
                            {displayName}
                          </p>
                          <p className="font-mono text-[11px] mt-1" style={{ color: 'var(--muted)' }}>
                            {isMandi ? 'MANDI DROP-OFF' : `${farm?.crop_type?.toUpperCase() || 'FARM'} PICKUP`}
                            {stop.load_kg ? ` · ${Math.round(stop.load_kg).toLocaleString()} kg` : (stock?.kg_at_risk ? ` · ${stock.kg_at_risk.toLocaleString()} kg` : '')}
                            {stock?.hours_until_spoilage != null ? ` · ${Math.round(stock.hours_until_spoilage)}h left` : ''}
                          </p>
                          {!isMandi && risk !== 'normal' && (
                            <span
                              className="font-mono uppercase tracking-wider inline-block mt-2 px-2 py-0.5"
                              style={{
                                fontSize: '9px',
                                color: RISK_COLORS[risk],
                                border: `1px solid ${RISK_COLORS[risk]}`,
                                borderRadius: '2px',
                              }}
                            >
                              {risk} weather risk
                            </span>
                          )}
                          {farm?.phone && (
                            <a
                              href={`tel:${farm.phone}`}
                              className="font-mono text-[10px] mt-2 inline-block px-2 py-1"
                              style={{
                                border: '1px solid var(--border)',
                                borderRadius: '4px',
                                color: 'var(--accent)',
                                textDecoration: 'none',
                                background: 'var(--accent-muted)',
                              }}
                            >
                              Call farmer {farm.phone}
                            </a>
                          )}
                        </div>
                        <div className="text-right flex-shrink-0 flex flex-col items-end gap-1">
                          {eta && (
                            <p className="font-mono text-[11px] font-semibold" style={{ color: 'var(--forest)' }}>
                              {eta}
                            </p>
                          )}
                          {minsLeft != null && (
                            <p
                              className="font-mono text-[10px]"
                              style={{ color: minsLeft < 0 ? 'var(--red-risk)' : 'var(--muted)' }}
                            >
                              {minsLeft < 0 ? `${Math.abs(minsLeft)}m late` : `in ${minsLeft}m`}
                            </p>
                          )}
                          {mapsUrl && (
                            <a
                              href={mapsUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn-primary mt-1"
                              style={{ padding: '6px 12px', fontSize: '10px', borderRadius: '6px', textDecoration: 'none' }}
                            >
                              Navigate ↗
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <AlternateStopsPanel planData={planData} currentStops={sortedStops} />

          {nearbyTrucks.length > 0 && (
            <div style={CARD}>
              <p className="font-mono uppercase text-[10px] tracking-widest px-5 pt-5 pb-3" style={{ color: 'var(--muted)' }}>
                Other drivers
              </p>
              <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
                {nearbyTrucks.slice(0, 5).map((t) => (
                  <a
                    key={t.id}
                    href={`tel:${t.driver_phone}`}
                    className="flex items-center justify-between px-5 py-4"
                    style={{ textDecoration: 'none' }}
                  >
                    <p className="font-syne font-bold text-[13px]" style={{ color: 'var(--navy)' }}>
                      {displayTruckId(t.id)}
                    </p>
                    <span
                      className="font-mono text-[11px] px-3 py-1.5"
                      style={{
                        background: 'var(--orange-muted)',
                        border: '1px solid rgba(244, 182, 62, 0.35)',
                        borderRadius: '6px',
                        color: 'var(--amber-warn)',
                        fontWeight: 600,
                      }}
                    >
                      {t.driver_phone}
                    </span>
                  </a>
                ))}
              </div>
            </div>
          )}

          {runId && truckId && (
            <button
              type="button"
              onClick={() => setShowBreakdown(true)}
              className="w-full py-3 font-mono uppercase tracking-wider"
              style={{
                fontSize: '11px',
                border: '1px solid var(--danger)',
                borderRadius: '4px',
                background: 'var(--red-muted)',
                color: 'var(--danger)',
                cursor: 'pointer',
              }}
            >
              Report breakdown
            </button>
          )}

          {showBreakdown && runId && truckId && (
            <BreakdownReportModal
              runId={runId}
              truckId={truckId}
              farmStops={farmStops}
              farmsById={new Map(DEMO_FARMS.map((f) => [f.id, f]))}
              reportOnly
              onClose={() => setShowBreakdown(false)}
              onReported={() => { setShowBreakdown(false); }}
            />
          )}
        </div>
      </DashboardLayout>
    </>
  );
}

export default withAuth(DriverDashboardPage, ['driver']);
