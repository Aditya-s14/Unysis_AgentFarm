import { formatKg } from '@/utils/formatters';
import {
  formatMarginBreakdown,
  formatMarginDelta,
  recommendationLabel,
  recommendationStyle,
} from '@/utils/farmEconomics';
import useFarmEconomics from '@/hooks/useFarmEconomics';

function EconomicsRow({ row, compact }) {
  const badgeStyle = recommendationStyle(row);

  return (
    <div
      className="px-4 py-4"
      style={{ borderTop: '1px solid var(--border)' }}
    >
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-3">
        <div>
          <p className="font-syne font-bold text-paper" style={{ fontSize: compact ? '12px' : '13px' }}>
            {row.farm_name}
          </p>
          <p className="font-mono text-muted mt-0.5" style={{ fontSize: '10px' }}>
            {row.crop_type}
            {' · sold '}
            {formatKg(row.sold_kg)}
            {' · waste '}
            {formatKg(row.waste_kg)}
          </p>
        </div>
        <span
          className="font-mono uppercase tracking-wider px-2 py-1 shrink-0 self-start"
          style={{ fontSize: '9px', borderRadius: '2px', ...badgeStyle }}
        >
          {recommendationLabel(row)}
        </span>
      </div>

      <div className={`grid gap-3 ${compact ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>
        <div
          className="p-3"
          style={{
            border: '1px solid var(--border)',
            borderRadius: '4px',
            background: 'var(--bg)',
          }}
        >
          <p className="font-mono uppercase text-muted" style={{ fontSize: '9px', letterSpacing: '0.14em' }}>
            APMC path (current VRP)
          </p>
          <p className="font-mono mt-2 text-muted" style={{ fontSize: '10px', lineHeight: 1.5 }}>
            {formatMarginBreakdown(
              row.apmc_revenue_inr,
              row.apmc_logistics_inr,
              row.apmc_spoilage_inr,
              row.apmc_net_margin_inr,
            )}
          </p>
        </div>

        <div
          className="p-3"
          style={{
            border: '1px solid var(--accent)',
            borderRadius: '4px',
            background: 'rgba(245, 166, 35, 0.06)',
          }}
        >
          <p className="font-mono uppercase" style={{ fontSize: '9px', letterSpacing: '0.14em', color: 'var(--accent)' }}>
            Direct buyer — {row.private_buyer_name}
          </p>
          <p className="font-mono mt-2" style={{ fontSize: '10px', lineHeight: 1.5, color: 'var(--text)' }}>
            {formatMarginBreakdown(
              row.direct_revenue_inr,
              row.direct_logistics_inr,
              row.direct_spoilage_inr,
              row.direct_net_margin_inr,
            )}
          </p>
        </div>
      </div>

      <p className="font-mono mt-2" style={{ fontSize: '10px', color: 'var(--accent)' }}>
        {formatMarginDelta(row.margin_delta_inr)}
      </p>
    </div>
  );
}

/**
 * Per-farm P&L: revenue − logistics − spoilage vs direct buyer offer.
 * Requires a completed scenario run (post-run only).
 */
export default function FarmEconomicsPanel({ compact = false, cachedRun = null }) {
  const { rows, loading, error, hasRun } = useFarmEconomics(cachedRun);

  return (
    <div
      className="bg-card"
      style={{
        border: '1px solid var(--border)',
        borderRadius: '4px',
      }}
    >
      <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <p
          className="font-mono uppercase"
          style={{ color: 'var(--accent)', fontSize: '0.65rem', letterSpacing: '0.15em' }}
        >
          ▸ Farm Economics
        </p>
        <p className="font-mono text-muted mt-1" style={{ fontSize: compact ? '10px' : '11px' }}>
          Net margin = revenue − logistics − spoilage. Compare APMC route vs direct buyer offer.
        </p>
      </div>

      {!hasRun && (
        <p className="px-4 py-6 font-mono text-muted text-[12px]">
          Run a scenario first to see farm economics.
        </p>
      )}

      {hasRun && loading && (
        <p className="px-4 py-6 font-mono text-muted text-[12px]">Calculating margins…</p>
      )}

      {error && (
        <p className="px-4 py-4 font-mono text-[11px]" style={{ color: 'var(--red-risk)' }}>
          {typeof error === 'string' ? error : JSON.stringify(error)}
        </p>
      )}

      {hasRun && !loading && !error && rows.length === 0 && (
        <p className="px-4 py-6 font-mono text-muted text-[12px]">
          No at-risk farms with price quotes for this run.
        </p>
      )}

      {rows.map((row) => (
        <EconomicsRow key={row.farm_id} row={row} compact={compact} />
      ))}
    </div>
  );
}
