import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { postTruckPosition, getRun } from '@/api/client';
import BreakdownReportModal from '@/components/Transport/BreakdownReportModal';
import AlternateStopsPanel from '@/components/Transport/AlternateStopsPanel';
import withAuth from '@/components/withAuth';
import { useAppContext } from '@/context/AppContext';
import { formatApiError } from '@/utils/api';
import { DEMO_TRUCKS, DEMO_FARMS, DEMO_DEMAND_POINTS } from '@/utils/demoFixtures';
import { displayTruckId } from '@/utils/truckDisplay';
import { etaFromMinutes, minutesUntilETA } from '@/utils/eta';

const SEND_INTERVAL_MS = 30000;

const RISK_COLORS = { severe: '#FF4444', warning: '#FF9800', normal: '#4CAF50' };

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

  // If URL truckId doesn't match user's entity_id, redirect to correct URL
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
    on_route: '#4CAF50', alert: '#FF4444', off_route: '#FF9800',
    error: '#FF4444', tracking: '#4CAF50', idle: '#8A9E8C',
  };

  return (
    <>
      <Head><title>Driver — {truckLabel}</title></Head>
      <main
        className="min-h-screen p-4 font-mono max-w-lg mx-auto"
        style={{ background: 'var(--bg)', color: 'var(--text)' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="font-syne font-bold uppercase text-paper" style={{ fontSize: '16px' }}>
              {truckLabel}
            </p>
            <p className="text-[11px]" style={{ color: 'var(--muted)' }}>
              Run {String(runId || '').slice(0, 8)}…
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div
                className="w-2.5 h-2.5 rounded-full"
                style={{ background: statusColors[status] || '#8A9E8C' }}
              />
              <span className="text-[11px] uppercase tracking-wider" style={{ color: statusColors[status] }}>
                {status.replace('_', ' ')}
              </span>
            </div>
            <Link
              href="/runs"
              style={{
                display: 'flex', alignItems: 'center', gap: '4px',
                background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                borderRadius: '6px', padding: '6px 10px', cursor: 'pointer',
                color: 'var(--text)', fontSize: '12px', fontFamily: 'monospace',
                textDecoration: 'none',
              }}
            >
              ← Runs
            </Link>
          </div>
        </div>

        {/* GPS status */}
        <div
          className="p-3 mb-4"
          style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
        >
          <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: 'var(--accent)' }}>
            GPS — posting every 30s
          </p>
          {lastPosition ? (
            <>
              <p className="text-[12px]">
                {lastPosition.lat.toFixed(5)}, {lastPosition.lng.toFixed(5)}
              </p>
              <p className="text-[11px] mt-0.5" style={{ color: 'var(--muted)' }}>
                Deviation: {lastPosition.deviation_km?.toFixed?.(1)} km
              </p>
            </>
          ) : (
            <p className="text-[11px]" style={{ color: 'var(--muted)' }}>Waiting for GPS fix…</p>
          )}
          {gpsError && (
            <p className="text-[11px] mt-1" style={{ color: 'var(--danger)' }}>{gpsError}</p>
          )}
        </div>

        {/* Stop List */}
        {sortedStops.length > 0 && (
          <div className="mb-4">
            <p className="text-[10px] uppercase tracking-widest mb-2" style={{ color: 'var(--muted)' }}>
              Route Stops ({sortedStops.length})
            </p>
            <div style={{ border: '1px solid var(--border)', borderRadius: '4px', overflow: 'hidden' }}>
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

                return (
                  <div
                    key={i}
                    style={{
                      borderTop: i === 0 ? 'none' : '1px solid var(--border)',
                      background: risk !== 'normal' && !isMandi ? `rgba(${risk === 'severe' ? '220,50,50' : '255,152,0'},0.04)` : 'transparent',
                    }}
                  >
                    <div className="flex items-start gap-3 px-3 py-3">
                      <div
                        className="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center mt-0.5"
                        style={{
                          background: isMandi ? 'var(--purple-log)' : RISK_COLORS[risk],
                          fontSize: '10px',
                          color: '#fff',
                          fontWeight: 700,
                        }}
                      >
                        {i + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] font-bold" style={{ color: isMandi ? 'var(--purple-log)' : 'var(--text)' }}>
                          {displayName}
                        </p>
                        <p className="text-[10px] mt-0.5" style={{ color: 'var(--muted)' }}>
                          {isMandi ? 'MANDI DROP-OFF' : `${farm?.crop_type?.toUpperCase() || 'FARM'} PICKUP`}
                          {stop.load_kg ? ` · ${Math.round(stop.load_kg).toLocaleString()} kg` : (stock?.kg_at_risk ? ` · ${stock.kg_at_risk.toLocaleString()} kg` : '')}
                          {stock?.hours_until_spoilage != null ? ` · ${Math.round(stock.hours_until_spoilage)}h left` : ''}
                        </p>
                        {!isMandi && risk !== 'normal' && (
                          <p className="text-[10px] uppercase tracking-wider mt-0.5" style={{ color: RISK_COLORS[risk] }}>
                            {risk} weather risk
                          </p>
                        )}
                        {farm?.phone && (
                          <a
                            href={`tel:${farm.phone}`}
                            className="text-[10px] mt-1 inline-block px-2 py-0.5"
                            style={{
                              border: '1px solid var(--border)',
                              borderRadius: '2px',
                              color: 'var(--accent)',
                              textDecoration: 'none',
                            }}
                          >
                            Call farmer {farm.phone}
                          </a>
                        )}
                      </div>
                      <div className="text-right flex-shrink-0 flex flex-col items-end gap-1">
                        {eta && <p className="text-[11px]" style={{ color: 'var(--accent)' }}>{eta}</p>}
                        {minsLeft != null && (
                          <p className="text-[10px]" style={{ color: minsLeft < 0 ? 'var(--red-risk)' : 'var(--muted)' }}>
                            {minsLeft < 0 ? `${Math.abs(minsLeft)}m late` : `in ${minsLeft}m`}
                          </p>
                        )}
                        {mapsUrl && (
                          <a
                            href={mapsUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[10px] px-2 py-1 mt-1"
                            style={{
                              background: 'var(--navy)',
                              color: '#fff',
                              borderRadius: '3px',
                              textDecoration: 'none',
                              fontWeight: 600,
                            }}
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

        {/* Alternate stop suggestions */}
        <AlternateStopsPanel planData={planData} currentStops={sortedStops} />

        {/* Nearby Drivers */}
        {nearbyTrucks.length > 0 && (
          <div className="mb-4">
            <p className="text-[10px] uppercase tracking-widest mb-2" style={{ color: 'var(--muted)' }}>
              Other Drivers
            </p>
            <div style={{ border: '1px solid var(--border)', borderRadius: '4px', overflow: 'hidden' }}>
              {nearbyTrucks.slice(0, 5).map((t, i) => (
                <a
                  key={t.id}
                  href={`tel:${t.driver_phone}`}
                  className="flex items-center justify-between px-3 py-3"
                  style={{
                    borderTop: i === 0 ? 'none' : '1px solid var(--border)',
                    textDecoration: 'none',
                    display: 'flex',
                  }}
                >
                  <p className="text-[13px] font-bold" style={{ color: 'var(--text)' }}>{displayTruckId(t.id)}</p>
                  <span
                    className="text-[11px] px-3 py-1.5"
                    style={{
                      background: 'rgba(94,234,212,0.1)',
                      border: '1px solid var(--accent)',
                      borderRadius: '3px',
                      color: 'var(--accent)',
                      fontWeight: 600,
                    }}
                  >
                    📞 {t.driver_phone}
                  </span>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Breakdown button */}
        {runId && truckId && (
          <button
            type="button"
            onClick={() => setShowBreakdown(true)}
            className="w-full py-3 font-mono uppercase tracking-wider mb-4"
            style={{
              fontSize: '11px',
              border: '1px solid var(--danger)',
              borderRadius: '4px',
              background: 'rgba(220,50,50,0.06)',
              color: 'var(--danger)',
              cursor: 'pointer',
            }}
          >
            Report Breakdown
          </button>
        )}

        <Link
          href="/runs"
          className="text-[12px] uppercase tracking-wider"
          style={{ color: 'var(--accent)' }}
        >
          ← Runs
        </Link>

        {showBreakdown && runId && truckId && (
          <BreakdownReportModal
            runId={runId}
            truckId={truckId}
            farmStops={farmStops}
            farmsById={new Map(DEMO_FARMS.map((f) => [f.id, f]))}
            onClose={() => setShowBreakdown(false)}
            onReported={() => { setShowBreakdown(false); }}
          />
        )}
      </main>
    </>
  );
}

export default withAuth(DriverDashboardPage, ['driver']);
