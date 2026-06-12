import { useCallback, useEffect, useState } from 'react';
import { getDeviationAlerts, getTruckTracking } from '@/api/client';
import { formatApiError } from '@/utils/api';

const DEFAULT_POLL_MS = 15000;

function pollInterval() {
  if (typeof window === 'undefined') return DEFAULT_POLL_MS;
  const raw = process.env.NEXT_PUBLIC_TRACKING_POLL_MS;
  const n = raw ? parseInt(raw, 10) : DEFAULT_POLL_MS;
  return Number.isFinite(n) && n >= 5000 ? n : DEFAULT_POLL_MS;
}

/**
 * Poll live truck GPS positions and deviation alerts for a dispatched run.
 */
export default function useTruckTracking(runId, enabled) {
  const [positions, setPositions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchTracking = useCallback(async () => {
    if (!runId || !enabled) {
      setPositions([]);
      setAlerts([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [tracking, deviation] = await Promise.all([
        getTruckTracking(runId),
        getDeviationAlerts(runId),
      ]);
      setPositions(tracking.positions || []);
      setAlerts(deviation.alerts || []);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [runId, enabled]);

  useEffect(() => {
    if (!enabled || !runId) return undefined;
    fetchTracking();
    const id = setInterval(fetchTracking, pollInterval());
    return () => clearInterval(id);
  }, [fetchTracking, enabled, runId]);

  const positionByTruck = positions.reduce((acc, p) => {
    acc[p.truck_id] = p;
    return acc;
  }, {});

  return {
    positions,
    positionByTruck,
    alerts,
    loading,
    error,
    refetch: fetchTracking,
  };
}
