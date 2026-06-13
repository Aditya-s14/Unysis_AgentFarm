import { useCallback, useEffect, useState } from 'react';
import {
  acceptMarketOffer,
  getMarketAccepted,
  getMarketOffers,
  postMarketOffer,
} from '@/api/client';
import { DEMO_MARKET_OFFERS } from '@/utils/demoFixtures';

const STORAGE_KEY = 'agentfarm_market_commitments';

function readCommitmentsStore() {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (Array.isArray(parsed)) return parsed;
    return DEMO_MARKET_OFFERS.commitments.map((c) => ({ ...c }));
  } catch {
    return DEMO_MARKET_OFFERS.commitments.map((c) => ({ ...c }));
  }
}

function writeCommitmentsStore(commitments) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(commitments));
  } catch {
    /* non-fatal */
  }
}

/** Read active market commitments for scenario submit. */
export function getMarketCommitmentsForApi() {
  return readCommitmentsStore().map((c) => ({
    offer_id: c.offer_id,
    farm_id: c.farm_id,
    demand_point_id: c.demand_point_id,
    crop_type: c.crop_type,
    quantity_kg: c.quantity_kg,
    price_per_kg: c.price_per_kg,
    accepted_at: c.accepted_at,
  }));
}

/**
 * D4 offer ledger — sync with /api/market/* and persist commitments locally.
 * @param {object} [options]
 * @param {function} [options.onAcceptCommitment] - (farmId, tonnageKg, demandPointId) => void
 */
export default function useMarketOffers({ onAcceptCommitment } = {}) {
  const [offers, setOffers] = useState([]);
  const [commitments, setCommitments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [acceptingId, setAcceptingId] = useState(null);
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [offersData, acceptedData] = await Promise.all([
        getMarketOffers(),
        getMarketAccepted(),
      ]);
      setOffers(offersData?.offers || []);
      const remote = acceptedData?.commitments;
      if (Array.isArray(remote) && remote.length > 0) {
        setCommitments(remote);
        writeCommitmentsStore(remote);
      } else {
        const local = readCommitmentsStore();
        setCommitments(local);
      }
    } catch (err) {
      setOffers(DEMO_MARKET_OFFERS.offers.map((o) => ({ ...o })));
      setCommitments(readCommitmentsStore());
      setError(err?.message || 'Failed to load market offers');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const isGuaranteed = useCallback(
    (farmId) => commitments.some((c) => c.farm_id === farmId),
    [commitments],
  );

  const getCommitment = useCallback(
    (farmId) => commitments.find((c) => c.farm_id === farmId) || null,
    [commitments],
  );

  const postOffer = useCallback(async (body) => {
    setPosting(true);
    setError(null);
    try {
      const data = await postMarketOffer(body);
      const saved = data?.offer;
      if (saved) {
        setOffers((prev) => [...prev.filter((o) => o.id !== saved.id), saved]);
      }
      return saved;
    } catch (err) {
      setError(err?.message || 'Failed to post offer');
      throw err;
    } finally {
      setPosting(false);
    }
  }, []);

  const acceptOffer = useCallback(async (offerId, farmId = null) => {
    setAcceptingId(offerId);
    setError(null);
    try {
      const body = farmId ? { offer_id: offerId, farm_id: farmId } : { offer_id: offerId };
      const resp = await acceptMarketOffer(body);
      const commitment = resp?.commitment;
      if (commitment) {
        setCommitments((prev) => {
          const next = [
            ...prev.filter((c) => c.offer_id !== commitment.offer_id),
            commitment,
          ];
          writeCommitmentsStore(next);
          return next;
        });
        if (onAcceptCommitment) {
          onAcceptCommitment(
            commitment.farm_id,
            commitment.quantity_kg,
            commitment.demand_point_id,
          );
        }
      }
      if (resp?.offer) {
        setOffers((prev) => prev.map((o) => (o.id === resp.offer.id ? resp.offer : o)));
      }
      return resp;
    } catch (err) {
      setError(err?.message || 'Accept failed');
      throw err;
    } finally {
      setAcceptingId(null);
    }
  }, [onAcceptCommitment]);

  const listCommitmentsForApi = useCallback(() => getMarketCommitmentsForApi(), []);

  return {
    offers,
    commitments,
    loading,
    error,
    acceptingId,
    posting,
    refresh,
    postOffer,
    acceptOffer,
    isGuaranteed,
    getCommitment,
    listCommitmentsForApi,
  };
}

export { readCommitmentsStore };
