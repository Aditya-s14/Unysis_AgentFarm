import { useMemo } from 'react';
import { DEMO_DEMAND_POINTS } from '@/utils/demoFixtures';
import useBuyerDemands from '@/hooks/useBuyerDemands';

const PRIVATE_DP_IDS = new Set(
  DEMO_DEMAND_POINTS.filter((d) => d.point_type === 'private').map((d) => d.id),
);

const APMC_DP_IDS = new Set(
  DEMO_DEMAND_POINTS.filter((d) => d.point_type === 'apmc').map((d) => d.id),
);

/**
 * After a scenario run: show how many route stops hit direct-buyer private DCs vs APMC.
 */
export default function BuyerRoutePriorityBanner({ plan }) {
  const { posts } = useBuyerDemands();

  const stats = useMemo(() => {
    const postDpIds = new Set(posts.map((p) => p.demand_point_id));
    const routes = plan?.routes || [];
    let privateWithPost = 0;
    let apmcStops = 0;
    const seen = new Set();

    for (const route of routes) {
      for (const stop of route.stops || []) {
        const dpId = stop.demand_point_id;
        if (!dpId || seen.has(`${route.truck_id}:${dpId}`)) continue;
        seen.add(`${route.truck_id}:${dpId}`);
        if (postDpIds.has(dpId) && PRIVATE_DP_IDS.has(dpId)) {
          privateWithPost += 1;
        } else if (APMC_DP_IDS.has(dpId)) {
          apmcStops += 1;
        }
      }
    }

    return { privateWithPost, apmcStops, hasPosts: posts.length > 0 };
  }, [plan, posts]);

  if (!stats.hasPosts || !plan?.routes?.length) return null;

  return (
    <div
      className="mt-6 px-4 py-3 font-mono"
      style={{
        border: '1px solid var(--accent)',
        borderRadius: '4px',
        background: 'rgba(245, 166, 35, 0.06)',
        fontSize: '11px',
        color: 'var(--text)',
      }}
    >
      <p className="uppercase tracking-wider text-accent" style={{ fontSize: '9px', letterSpacing: '0.14em' }}>
        Direct buyer routing
      </p>
      <p className="mt-2 leading-relaxed">
        Direct buyer demand fulfilled first
        {' '}
        (
        <span className="text-accent">{stats.privateWithPost}</span>
        {' '}
        private DC stop
        {stats.privateWithPost !== 1 ? 's' : ''}
        with active posts); remainder routed to APMC
        {' '}
        (
        <span className="text-muted">{stats.apmcStops}</span>
        {' '}
        mandi stop
        {stats.apmcStops !== 1 ? 's' : ''}
        ).
        Bypasses inefficient mandi middlemen for posted private demand.
      </p>
    </div>
  );
}
