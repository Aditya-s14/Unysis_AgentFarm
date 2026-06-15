import { useCallback, useEffect, useState } from 'react';
import { getRun, getRunTraces } from '@/api/client';
import { formatApiError } from '@/utils/api';

const LAST_RESPONSE_KEY = 'agentfarm_last_response';

function readCachedResponse() {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(LAST_RESPONSE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Hook that fetches a single run (plan + KPI summary) by id.
 * Pass `null`/`undefined` to disable the fetch.
 */
export function useRun(runId) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchRun = useCallback(async () => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getRun(runId);
      setData(result);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    fetchRun();
  }, [fetchRun]);

  return { data, loading, error, refetch: fetchRun };
}

/** Hook that fetches the agent traces for a run. */
export function useRunTraces(runId) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchTraces = useCallback(async () => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getRunTraces(runId);
      setData(result);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    fetchTraces();
  }, [fetchTraces]);

  return { data, loading, error, refetch: fetchTraces };
}

/**
 * Hook that returns the user-visible list of runs.
 *
 * Backend has no `/api/runs` list endpoint yet, so we synthesise a one-row
 * list from the response cached by ScenarioForm in localStorage.  This is
 * enough for the demo (Dashboard "Recent Runs" + Runs sidebar).
 */
export function useRuns() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchRuns = useCallback(() => {
    setLoading(true);
    setError(null);
    try {
      const cached = readCachedResponse();
      if (!cached?.run_id) {
        setData([]);
        return;
      }
      const wastePct = cached.kpis?.waste_reduction_pct ?? 0;
      setData([
        {
          runId: cached.run_id,
          scenarioType: cached.scenario_type || 'monsoon_disruption',
          createdAt: new Date().toISOString(),
          // KPIGrid / dashboard treat this as a fraction (0–1); backend returns 0–100.
          wasteReductionPct: wastePct / 100,
        },
      ]);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  return { data, loading, error, refetch: fetchRuns };
}

/** Read the cached POST /api/scenario/run response. */
export function useCachedRunResponse() {
  const [data, setData] = useState(null);

  useEffect(() => {
    setData(readCachedResponse());
  }, []);

  return data;
}

export default useRuns;
