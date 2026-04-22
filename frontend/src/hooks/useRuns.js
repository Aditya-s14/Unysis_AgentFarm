import { useCallback, useEffect, useState } from 'react';
import { getRun, getRunTraces } from '@/api/client';
import { formatApiError } from '@/utils/api';

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
 * Hook that returns the list of runs.
 * TODO: wire to a real `/api/runs` list endpoint when backend adds one.
 * For now, returns mock data so the Runs page can render.
 */
export function useRuns() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // TODO: replace with real API call when backend exposes list endpoint.
      const mock = [
        {
          runId: 'run_demo_001',
          scenarioType: 'monsoon_disruption',
          createdAt: '2026-04-20T09:12:00Z',
          wasteReductionPct: 0.27,
        },
        {
          runId: 'run_demo_002',
          scenarioType: 'heat_wave',
          createdAt: '2026-04-21T14:03:00Z',
          wasteReductionPct: 0.21,
        },
      ];
      setData(mock);
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

export default useRuns;
