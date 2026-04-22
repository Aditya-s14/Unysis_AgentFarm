/**
 * KPICard — single metric tile with title, value, and a delta-vs-baseline badge.
 * `delta` is interpreted as a signed fractional change (e.g. 0.23 → +23%).
 * `improvementDirection` ("up"|"down") indicates which direction is good.
 */
export default function KPICard({
  title,
  value,
  delta,
  improvementDirection = 'up',
  subtitle,
}) {
  let badgeClass = 'bg-gray-100 text-gray-600';
  let badgeLabel = '--';

  if (typeof delta === 'number' && !Number.isNaN(delta)) {
    const isPositive = delta >= 0;
    const isImprovement =
      (improvementDirection === 'up' && isPositive) ||
      (improvementDirection === 'down' && !isPositive);
    badgeClass = isImprovement
      ? 'bg-green-100 text-green-700'
      : 'bg-red-100 text-red-700';
    const sign = isPositive ? '+' : '';
    badgeLabel = `${sign}${(delta * 100).toFixed(1)}%`;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-gray-500">{title}</p>
      <div className="mt-2 flex items-baseline justify-between">
        <span className="text-2xl font-bold text-agri-green-dark">{value}</span>
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${badgeClass}`}>
          {badgeLabel}
        </span>
      </div>
      {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
    </div>
  );
}
