import { CHECK, WARN } from '@/utils/uiChars';

/**
 * 2–3 operational alerts derived from mandi fulfilment rows + scenario/weather context.
 * Display-only — does not alter fulfilment calculations.
 */
export default function MandiRiskHighlights({ rows, cached, delayedRouteCount }) {
  const alerts = [];

  const heavyShort = (rows || []).filter((r) => r.shortageKg > 500);
  if (heavyShort.length > 0) {
    alerts.push(
      `${WARN} ${heavyShort.length} mandi${heavyShort.length !== 1 ? 's' : ''} projected to face shortage >500 kg`,
    );
  }

  const covered = (rows || []).filter(
    (r) => r.statusLabel === 'SUPPLY MET' || r.statusLabel === 'EXCESS',
  );
  if (covered.length > 0) {
    alerts.push(
      `${CHECK} ${covered.length} mandi${covered.length !== 1 ? 's' : ''} fully covered`,
    );
  }

  const scenario = (cached?.scenario_type || cached?.weather_summary?.scenario_type || '')
    .toLowerCase();
  const isMonsoon = scenario.includes('monsoon');
  const delayed = Number(delayedRouteCount) || 0;

  if (isMonsoon && delayed > 0) {
    alerts.push(
      `Transport: monsoon delay affecting ${delayed} incoming route${delayed !== 1 ? 's' : ''}`,
    );
  } else {
    const advisory = cached?.weather_summary?.transport_advisory;
    if (advisory && typeof advisory === 'string' && advisory.length > 0) {
      const short = advisory.length > 72 ? `${advisory.slice(0, 69)}…` : advisory;
      alerts.push(`Transport: ${short}`);
    }
  }

  const stable = alerts.length === 0;

  return (
    <div
      className="px-5 py-4"
      style={{
        border: '1px solid var(--border)',
        borderLeft: '3px solid var(--accent)',
        borderRadius: '4px',
        background: 'rgba(245, 166, 35, 0.04)',
      }}
    >
      <p
        className="font-mono uppercase text-muted mb-3"
        style={{ fontSize: '9px', letterSpacing: '0.18em' }}
      >
        Risk highlights
      </p>
      {stable ? (
        <p className="font-mono" style={{ fontSize: '12px', color: 'var(--green-ok)' }}>
          All mandis stable
        </p>
      ) : (
        <ul className="space-y-2">
          {alerts.slice(0, 3).map((text) => (
            <li
              key={text}
              className="font-mono text-paper"
              style={{ fontSize: '12px', lineHeight: 1.55 }}
            >
              {text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
