import { useCallback, useEffect, useState } from 'react';
import { getFarmMargins } from '@/api/client';
import { DEMO_DEMAND_POINTS, DEMO_FARMS, DEMO_TRUCKS } from '@/utils/demoFixtures';

const LAST_RESPONSE_KEY = 'agentfarm_last_response';

function readCachedRun() {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(LAST_RESPONSE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function buildMarginsPayload(cached) {
  if (!cached?.at_risk_stock?.length) return null;
  const routePlan = cached?.plan?.route_plan;
  if (!routePlan?.routes?.length) return null;

  return {
    farms: cached.farms?.length ? cached.farms : DEMO_FARMS,
    demand_points: cached.demand_points?.length ? cached.demand_points : DEMO_DEMAND_POINTS,
    trucks: DEMO_TRUCKS,
    at_risk_stock: cached.at_risk_stock,
    route_plan: routePlan,
  };
}

/**
 * Fetch per-farm P&L from cached scenario run (post-run only).
 */
export default function useFarmEconomics(cachedOverride = null) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasRun, setHasRun] = useState(false);

  const fetchMargins = useCallback(async (cached) => {
    const payload = buildMarginsPayload(cached);
    setHasRun(Boolean(payload));
    if (!payload) {
      setRows([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getFarmMargins(payload);
      setRows(data?.rows || []);
    } catch (err) {
      setError(
        err?.response?.data?.detail
        || err?.message
        || 'Failed to load farm economics',
      );
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const cached = cachedOverride ?? readCachedRun();
    fetchMargins(cached);
  }, [cachedOverride, fetchMargins]);

  const refetch = useCallback(() => {
    fetchMargins(cachedOverride ?? readCachedRun());
  }, [cachedOverride, fetchMargins]);

  return { rows, loading, error, hasRun, refetch };
}
