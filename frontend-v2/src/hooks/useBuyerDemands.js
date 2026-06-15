import { useCallback, useEffect, useState } from 'react';
import {
  deleteBuyerDemand,
  getBuyerDemands,
  postBuyerDemand,
} from '@/api/client';
import { DEMO_BUYER_DEMANDS } from '@/utils/demoFixtures';

const STORAGE_KEY = 'agentfarm_buyer_demands';

function readStore() {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    return DEMO_BUYER_DEMANDS.map((p) => ({ ...p }));
  } catch {
    return DEMO_BUYER_DEMANDS.map((p) => ({ ...p }));
  }
}

function writeStore(posts) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(posts));
  } catch {
    /* non-fatal */
  }
}

/** Read active buyer posts from localStorage (for scenario submit). */
export function getBuyerDemandsForApi() {
  return readStore().map((p) => ({
    id: p.id,
    demand_point_id: p.demand_point_id,
    buyer_name: p.buyer_name,
    buyer_type: p.buyer_type,
    crop_type: p.crop_type,
    quantity_kg: p.quantity_kg,
    price_per_kg: p.price_per_kg,
    ...(p.posted_at ? { posted_at: p.posted_at } : {}),
  }));
}

/**
 * Persist direct buyer demand posts in localStorage + sync with backend API.
 */
export default function useBuyerDemands() {
  const [posts, setPosts] = useState([]);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    setPosts(readStore());
    setSyncing(true);
    getBuyerDemands()
      .then((data) => {
        const remote = data?.posts;
        if (Array.isArray(remote) && remote.length > 0) {
          setPosts(remote);
          writeStore(remote);
        }
      })
      .catch(() => {
        /* offline — keep localStorage */
      })
      .finally(() => setSyncing(false));
  }, []);

  const postDemand = useCallback(async (body) => {
    const optimisticId = `buyer-${body.demand_point_id}-${body.crop_type.toLowerCase()}`;
    const optimistic = {
      id: optimisticId,
      ...body,
      posted_at: new Date().toISOString(),
    };
    setPosts((prev) => {
      const filtered = prev.filter(
        (p) => !(p.demand_point_id === body.demand_point_id
          && p.crop_type.toLowerCase() === body.crop_type.toLowerCase()),
      );
      const next = [...filtered, optimistic];
      writeStore(next);
      return next;
    });
    try {
      const data = await postBuyerDemand(body);
      const saved = data?.post;
      if (saved) {
        setPosts((prev) => {
          const next = [
            ...prev.filter((p) => p.id !== optimisticId && p.id !== saved.id),
            saved,
          ];
          writeStore(next);
          return next;
        });
      }
      return saved;
    } catch (err) {
      setPosts(readStore());
      throw err;
    }
  }, []);

  const removePost = useCallback(async (postId) => {
    setPosts((prev) => {
      const next = prev.filter((p) => p.id !== postId);
      writeStore(next);
      return next;
    });
    try {
      await deleteBuyerDemand(postId);
    } catch {
      setPosts(readStore());
    }
  }, []);

  const listForApi = useCallback(() => getBuyerDemandsForApi(), []);

  return {
    posts,
    syncing,
    postDemand,
    removePost,
    listForApi,
  };
}
