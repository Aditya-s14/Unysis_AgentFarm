import { useCallback, useEffect, useState } from 'react';
import { logOutcome } from '@/api/client';
import { formatApiError } from '@/utils/api';
import { buildMandiOutcomePayload } from '@/utils/outcomePayload';

const storageKey = (runId) => `agentfarm_outcomes_${runId}`;

function loadLoggedMandiIds(runId) {
  if (!runId || typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(storageKey(runId));
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function persistLoggedMandiIds(runId, ids) {
  if (!runId || typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(storageKey(runId), JSON.stringify(ids));
  } catch {
    /* non-fatal */
  }
}

/**
 * Wrap POST /api/outcome/log and track logged mandi IDs per run.
 */
export default function useOutcomeLog(runId) {
  const [loggedMandiIds, setLoggedMandiIds] = useState([]);
  const [logging, setLogging] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoggedMandiIds(loadLoggedMandiIds(runId));
  }, [runId]);

  const markLogged = useCallback((mandiId) => {
    setLoggedMandiIds((prev) => {
      if (prev.includes(mandiId)) return prev;
      const next = [...prev, mandiId];
      persistLoggedMandiIds(runId, next);
      return next;
    });
  }, [runId]);

  const logMandiOutcome = useCallback(async ({
    mandiRow,
    cached,
    rawRoutes,
    farms,
    actualOverrides = {},
  }) => {
    if (!runId || !mandiRow?.id) {
      throw new Error('Missing run or mandi context');
    }
    if (loggedMandiIds.includes(mandiRow.id)) {
      throw new Error('Outcome already logged for this mandi');
    }

    setLogging(true);
    setError(null);
    try {
      const payload = await buildMandiOutcomePayload({
        cached,
        mandiRow,
        rawRoutes,
        farms,
        runId,
        actualOverrides,
      });
      await logOutcome(payload);
      markLogged(mandiRow.id);
      return payload;
    } catch (err) {
      const msg = formatApiError(err);
      setError(msg);
      throw err;
    } finally {
      setLogging(false);
    }
  }, [runId, loggedMandiIds, markLogged]);

  const isLogged = useCallback(
    (mandiId) => loggedMandiIds.includes(mandiId),
    [loggedMandiIds],
  );

  return {
    logMandiOutcome,
    logging,
    error,
    loggedMandiIds,
    isLogged,
  };
}
