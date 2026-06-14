import { useCallback, useState } from 'react';
import { runScenario } from '@/api/client';
import { formatApiError } from '@/utils/api';

/**
 * Hook to trigger a scenario run against the backend pipeline.
 * Unlike read hooks, this one is imperative — callers invoke `run(body)`.
 */
export function useScenario() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const run = useCallback(async (body) => {
    setLoading(true);
    setError(null);
    try {
      const result = await runScenario(body);
      setData(result);
      return result;
    } catch (err) {
      setError(formatApiError(err));
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return { data, loading, error, run, reset };
}

export default useScenario;
