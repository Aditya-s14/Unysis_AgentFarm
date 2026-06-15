import { useCallback, useEffect, useState } from 'react';
import { logOutcome } from '@/api/client';
import { formatApiError } from '@/utils/api';
import { buildMandiOutcomePayload } from '@/utils/outcomePayload';

const storageKey = (runId) => `agentfarm_outcomes_${runId}`;

function truckLogKey(mandiId, truckId) {
  return `${mandiId}::${truckId}`;
}

function loadLoggedKeys(runId) {
  if (!runId || typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(storageKey(runId));
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function persistLoggedKeys(runId, keys) {
  if (!runId || typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(storageKey(runId), JSON.stringify(keys));
  } catch {
    /* non-fatal */
  }
}

/**
 * Wrap POST /api/outcome/log and track logged mandi IDs per run.
 */
export default function useOutcomeLog(runId) {
  const [loggedKeys, setLoggedKeys] = useState([]);
  const [logging, setLogging] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoggedKeys(loadLoggedKeys(runId));
  }, [runId]);

  const markLogged = useCallback((mandiId, truckId) => {
    const key = truckId ? truckLogKey(mandiId, truckId) : mandiId;
    setLoggedKeys((prev) => {
      if (prev.includes(key)) return prev;
      const next = [...prev, key];
      persistLoggedKeys(runId, next);
      return next;
    });
  }, [runId]);

  const logMandiOutcome = useCallback(async ({
    mandiRow,
    truck,
    cached,
    rawRoutes,
    farms,
    actualOverrides = {},
  }) => {
    if (!runId || !mandiRow?.id) {
      throw new Error('Missing run or mandi context');
    }
    if (!truck?.truck_id) {
      throw new Error('Select a truck to confirm delivery');
    }
    const key = truckLogKey(mandiRow.id, truck.truck_id);
    if (loggedKeys.includes(key)) {
      throw new Error('Outcome already logged for this truck');
    }

    setLogging(true);
    setError(null);
    try {
      const payload = await buildMandiOutcomePayload({
        cached,
        mandiRow,
        truck,
        rawRoutes,
        farms,
        runId,
        actualOverrides,
      });
      await logOutcome(payload);
      markLogged(mandiRow.id, truck.truck_id);
      return payload;
    } catch (err) {
      const msg = formatApiError(err);
      setError(msg);
      throw err;
    } finally {
      setLogging(false);
    }
  }, [runId, loggedKeys, markLogged]);

  const isTruckLogged = useCallback(
    (mandiId, truckId) => loggedKeys.includes(truckLogKey(mandiId, truckId)),
    [loggedKeys],
  );

  const isLogged = useCallback(
    (mandiId, trucks = []) => {
      const withLoad = trucks.filter((t) => (t.load_kg ?? 0) > 0);
      if (withLoad.length === 0) return loggedKeys.includes(mandiId);
      return withLoad.every((t) => isTruckLogged(mandiId, t.truck_id));
    },
    [loggedKeys, isTruckLogged],
  );

  return {
    logMandiOutcome,
    logging,
    error,
    loggedKeys,
    isLogged,
    isTruckLogged,
  };
}
