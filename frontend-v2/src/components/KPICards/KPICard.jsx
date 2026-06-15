/**
 * KPICard — mission-control metric tile.
 * Top accent bar, heading weight number, uppercase label.
 *
 * Props:
 *   title                 short uppercase label
 *   value                 already-formatted string (e.g. "56.0%", "2,500 kg")
 *   delta                 signed fraction (e.g. 0.56 → ↑56.0% in OK colour)
 *   improvementDirection  "up" | "down" — which way is good
 *   subtitle              short helper line under the badge row
 */
export default function KPICard({
  title,
  value,
  delta,
  improvementDirection = 'up',
  subtitle,
}) {
  let badgeColor = 'var(--muted)';
  let badgeLabel = '—';

  if (typeof delta === 'number' && !Number.isNaN(delta)) {
    const isPositive = delta >= 0;
    const isImprovement =
      (improvementDirection === 'up' && isPositive) ||
      (improvementDirection === 'down' && !isPositive);
    badgeColor = isImprovement ? 'var(--green-ok)' : 'var(--red-risk)';
    const arrow = isPositive ? '↑' : '↓';
    badgeLabel = `${arrow}${Math.abs(delta * 100).toFixed(1)}%`;
  }

  return (
    <div
      className="bg-card relative p-5"
      style={{
        border: '1px solid var(--border)',
        borderTop: '3px solid var(--accent)',
        borderRadius: '4px',
      }}
    >
      <p
        className="font-mono text-muted uppercase"
        style={{ fontSize: '0.7rem', letterSpacing: '0.1em' }}
      >
        {title}
      </p>
      <div className="mt-3 flex items-baseline justify-between gap-2">
        <span
          className="font-syne font-bold leading-none"
          style={{ color: 'var(--accent)', fontSize: '2rem' }}
        >
          {value}
        </span>
        <span
          className="font-mono text-[11px] px-2 py-0.5"
          style={{
            color: badgeColor,
            border: `1px solid ${badgeColor}`,
            borderRadius: '2px',
            letterSpacing: '0.05em',
          }}
        >
          {badgeLabel}
        </span>
      </div>
      {subtitle && (
        <p className="mt-2 font-mono text-muted text-[11px] uppercase tracking-wider">
          {subtitle}
        </p>
      )}
    </div>
  );
}
