import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'agentfarm_farmer_commitments';

function readStore() {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

/** Read locked commitments from localStorage (for scenario submit). */
export function getCommitmentsForApi() {
  return Object.entries(readStore())
    .filter(([, v]) => v?.locked && v.tonnage_kg > 0)
    .map(([farm_id, v]) => ({
      farm_id,
      tonnage_kg: v.tonnage_kg,
      ...(v.demand_point_id ? { demand_point_id: v.demand_point_id } : {}),
    }));
}

function writeStore(data) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    /* non-fatal */
  }
}

/**
 * Persist farmer pre-commitment contracts in localStorage for scenario runs.
 */
export default function useFarmerCommitments() {
  const [commitments, setCommitments] = useState({});

  useEffect(() => {
    setCommitments(readStore());
  }, []);

  const lockCommitment = useCallback((farmId, { tonnage_kg, demand_point_id }) => {
    setCommitments((prev) => {
      const next = {
        ...prev,
        [farmId]: {
          tonnage_kg: Number(tonnage_kg),
          demand_point_id: demand_point_id || null,
          locked: true,
        },
      };
      writeStore(next);
      return next;
    });
  }, []);

  const unlockCommitment = useCallback((farmId) => {
    setCommitments((prev) => {
      const next = { ...prev };
      delete next[farmId];
      writeStore(next);
      return next;
    });
  }, []);

  const isLocked = useCallback(
    (farmId) => Boolean(commitments[farmId]?.locked),
    [commitments],
  );

  const getCommitment = useCallback(
    (farmId) => commitments[farmId] || null,
    [commitments],
  );

  /** Array shape for POST /api/scenario/run */
  const listForApi = useCallback(
    () => Object.entries(commitments)
      .filter(([, v]) => v?.locked && v.tonnage_kg > 0)
      .map(([farm_id, v]) => ({
        farm_id,
        tonnage_kg: v.tonnage_kg,
        ...(v.demand_point_id ? { demand_point_id: v.demand_point_id } : {}),
      })),
    [commitments],
  );

  const summary = useCallback(() => {
    const locked = listForApi();
    const totalKg = locked.reduce((s, c) => s + c.tonnage_kg, 0);
    return { count: locked.length, totalKg };
  }, [listForApi]);

  return {
    commitments,
    lockCommitment,
    unlockCommitment,
    isLocked,
    getCommitment,
    listForApi,
    summary,
  };
}
