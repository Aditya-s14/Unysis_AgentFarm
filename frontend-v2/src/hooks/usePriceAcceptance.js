import { useCallback, useEffect, useState } from 'react';
import { acceptPrivateOffer, getPriceBoard } from '@/api/client';

const STORAGE_KEY = 'agentfarm_price_accepts';

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

function writeStore(data) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    /* non-fatal */
  }
}

/**
 * Price board fetch + private offer acceptance (D1).
 * @param {object} [options]
 * @param {function} [options.onAcceptCommitment] - (farmId, tonnageKg, privateMandiId) => void
 */
export default function usePriceAcceptance({ onAcceptCommitment } = {}) {
  const [quotes, setQuotes] = useState([]);
  const [accepted, setAccepted] = useState({});
  const [loading, setLoading] = useState(true);
  const [acceptingId, setAcceptingId] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPriceBoard();
      setQuotes(data.quotes || []);
      const merged = { ...readStore(), ...(data.accepted || {}) };
      setAccepted(merged);
      writeStore(merged);
    } catch (err) {
      setError(err?.message || 'Failed to load price board');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const isAccepted = useCallback(
    (farmId) => Boolean(accepted[farmId]),
    [accepted],
  );

  const getAcceptance = useCallback(
    (farmId) => accepted[farmId] || null,
    [accepted],
  );

  const acceptOffer = useCallback(async (quote, channel = 'private') => {
    if (!quote?.farm_id) return null;
    setAcceptingId(`${quote.farm_id}:${channel}`);
    setError(null);
    try {
      const pricePerKg = channel === 'apmc'
        ? quote.apmc_price_per_kg
        : quote.private_offer_per_kg;
      const body = {
        farm_id: quote.farm_id,
        crop_type: quote.crop_type,
        apmc_demand_point_id: quote.apmc_demand_point_id,
        private_demand_point_id: quote.private_demand_point_id,
        accepted_price_per_kg: pricePerKg,
        tonnage_kg: quote.tonnage_kg,
        channel,
      };
      const resp = await acceptPrivateOffer(body);
      const record = resp.acceptance || body;
      setAccepted((prev) => {
        const next = { ...prev, [quote.farm_id]: record };
        writeStore(next);
        return next;
      });
      if (onAcceptCommitment && channel === 'private') {
        onAcceptCommitment(
          quote.farm_id,
          quote.tonnage_kg,
          quote.private_demand_point_id,
        );
      }
      return resp;
    } catch (err) {
      if (err?.response?.status === 409 && err?.response?.data?.detail?.acceptance) {
        const record = err.response.data.detail.acceptance;
        setAccepted((prev) => {
          const next = { ...prev, [quote.farm_id]: record };
          writeStore(next);
          return next;
        });
        return err.response.data.detail;
      }
      setError(err?.message || 'Accept failed');
      throw err;
    } finally {
      setAcceptingId(null);
    }
  }, [onAcceptCommitment]);

  return {
    quotes,
    accepted,
    loading,
    error,
    acceptingId,
    refresh,
    isAccepted,
    getAcceptance,
    acceptOffer,
  };
}

export { readStore as readPriceAcceptanceStore };
