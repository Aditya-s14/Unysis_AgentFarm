import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { postTruckPosition } from '@/api/client';
import { formatApiError } from '@/utils/api';
import { displayTruckId } from '@/utils/truckDisplay';

const SEND_INTERVAL_MS = 30000;

/**
 * Minimal driver page — posts phone GPS to the tracking API.
 */
export default function DriverGpsPage() {
  const router = useRouter();
  const { runId, truckId } = router.query;
  const [status, setStatus] = useState('idle');
  const [lastPosition, setLastPosition] = useState(null);
  const [error, setError] = useState(null);
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
      setError(null);
    } catch (err) {
      setError(formatApiError(err));
      setStatus('error');
    }
  }, [runId, truckId]);

  useEffect(() => {
    if (!runId || !truckId || typeof window === 'undefined') return undefined;
    if (!navigator.geolocation) {
      setError('Geolocation not supported on this device');
      return undefined;
    }

    const onPosition = (pos) => {
      sendPosition(pos.coords);
    };
    const onError = (err) => {
      setError(err.message || 'Geolocation error');
      setStatus('error');
    };

    watchIdRef.current = navigator.geolocation.watchPosition(onPosition, onError, {
      enableHighAccuracy: true,
      maximumAge: 10000,
      timeout: 20000,
    });

    intervalRef.current = setInterval(() => {
      navigator.geolocation.getCurrentPosition(onPosition, onError, {
        enableHighAccuracy: true,
        timeout: 15000,
      });
    }, SEND_INTERVAL_MS);

    setStatus('tracking');

    return () => {
      if (watchIdRef.current != null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [runId, truckId, sendPosition]);

  const label = truckId ? displayTruckId(String(truckId)) : 'Truck';

  return (
    <>
      <Head><title>Driver GPS | {label}</title></Head>
      <main
        className="min-h-screen p-6 font-mono"
        style={{ background: 'var(--bg)', color: 'var(--text)' }}
      >
        <p className="font-syne font-bold uppercase text-paper mb-2" style={{ fontSize: '18px' }}>
          Driver GPS — {label}
        </p>
        <p className="text-muted text-[12px] mb-4">
          Run {String(runId || '').slice(0, 8)}… · posting location every 30s
        </p>

        <div
          className="p-4 mb-4"
          style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
        >
          <p className="text-[11px] uppercase tracking-wider m-0" style={{ color: 'var(--accent)' }}>
            Status: {status.replace('_', ' ')}
          </p>
          {lastPosition && (
            <>
              <p className="text-[12px] mt-2 m-0">
                {lastPosition.lat.toFixed(5)}, {lastPosition.lng.toFixed(5)}
              </p>
              <p className="text-[12px] mt-1 m-0 text-muted">
                Deviation: {lastPosition.deviation_km?.toFixed?.(1)} km
              </p>
            </>
          )}
          {error && (
            <p className="text-[12px] mt-2 m-0" style={{ color: 'var(--danger)' }}>{error}</p>
          )}
        </div>

        <Link
          href="/dashboard"
          className="text-[12px] uppercase tracking-wider"
          style={{ color: 'var(--accent)' }}
        >
          ← Back to dashboard
        </Link>
      </main>
    </>
  );
}
