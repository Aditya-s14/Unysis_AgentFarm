/**
 * ScenarioTypeSelect — disruption templates as selectable cards or compact pills.
 */
const OPTIONS = [
  {
    id: 'monsoon_disruption',
    label: 'Monsoon Disruption',
    shortLabel: 'MONSOON',
    tag: 'High impact',
    tagColor: 'var(--blue-mandi)',
    tagBg: 'var(--blue-muted)',
    icon: '🌧',
    description:
      'Heavy rain in coastal / Western Ghats farms; shelf life −20%; affected road legs ×1.3 travel time.',
  },
  {
    id: 'heat_wave',
    label: 'Heat Wave',
    shortLabel: 'HEAT',
    tag: 'Critical',
    tagColor: 'var(--red-risk)',
    tagBg: 'var(--red-muted)',
    icon: '🌡',
    description:
      'Temperatures ≥39°C; shelf life −40%; morning-delivery bias on urgent farm→mandi routes.',
  },
  {
    id: 'normal_day',
    label: 'Normal Day',
    shortLabel: 'NORMAL',
    tag: 'Baseline',
    tagColor: 'var(--green-ok)',
    tagBg: 'var(--green-muted)',
    icon: '☀',
    description:
      'Baseline weather and routing; no scenario stress overlays on shelf life or distances.',
  },
  {
    id: 'live_weather',
    label: 'Live Weather',
    shortLabel: 'LIVE',
    tag: 'Real-time',
    tagColor: 'var(--accent-light)',
    tagBg: 'var(--accent-muted)',
    icon: '📡',
    description:
      'OpenWeather at each farm — shelf life and routing stress follow observed rain and temperature.',
  },
];

const PIPELINE_STEPS = [
  'Weather',
  'Demand',
  'Inventory',
  'Logistics',
  'Validator',
  'Orchestrator',
];

export function ScenarioPipelinePreview() {
  return (
    <div
      className="p-4"
      style={{
        background: 'var(--bg-subtle)',
        border: '1px solid var(--border)',
        borderRadius: '4px',
      }}
    >
      <p
        className="font-mono uppercase mb-3"
        style={{ fontSize: '9px', letterSpacing: '0.14em', color: 'var(--muted)' }}
      >
        Agent pipeline
      </p>
      <div className="flex flex-wrap items-center gap-1.5">
        {PIPELINE_STEPS.map((step, i) => (
          <span key={step} className="inline-flex items-center gap-1.5">
            <span
              className="font-mono uppercase px-2 py-1"
              style={{
                fontSize: '9px',
                letterSpacing: '0.08em',
                borderRadius: '2px',
                border: '1px solid var(--border)',
                background: 'var(--bg-card)',
                color: 'var(--text)',
              }}
            >
              {String(i + 1).padStart(2, '0')} {step}
            </span>
            {i < PIPELINE_STEPS.length - 1 && (
              <span style={{ color: 'var(--muted)', fontSize: '10px' }}>→</span>
            )}
          </span>
        ))}
      </div>
      <p className="font-mono text-muted mt-3" style={{ fontSize: '10px', lineHeight: 1.5 }}>
        ~30s end-to-end · routes, forecasts, and at-risk stock written to your dashboard
      </p>
    </div>
  );
}

export default function ScenarioTypeSelect({ value, onChange, layout = 'cards' }) {
  const active = OPTIONS.find((o) => o.id === value) || OPTIONS[0];

  if (layout === 'pills') {
    return (
      <div>
        <p
          className="font-mono text-muted uppercase mb-2"
          style={{ fontSize: '0.7rem', letterSpacing: '0.1em' }}
        >
          Scenario Type
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          {OPTIONS.map((opt) => {
            const isActive = value === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => onChange(opt.id)}
                className="font-mono text-[11px] py-3 px-3 transition tracking-wider-2 text-left"
                style={{
                  background: isActive ? 'var(--accent)' : 'transparent',
                  color: isActive ? 'var(--accent-text)' : 'var(--muted)',
                  border: isActive ? '1px solid var(--accent)' : '1px solid var(--border)',
                  borderRadius: '2px',
                  fontWeight: isActive ? 600 : 400,
                }}
              >
                {opt.shortLabel}
              </button>
            );
          })}
        </div>
        <p className="font-mono text-muted mt-3 leading-relaxed" style={{ fontSize: '11px' }}>
          {active.description}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div>
        <p
          className="font-syne font-bold uppercase text-paper tracking-wider"
          style={{ fontSize: '13px' }}
        >
          Choose disruption scenario
        </p>
        <p className="font-mono text-muted mt-1" style={{ fontSize: '11px', lineHeight: 1.5 }}>
          Pick how today&apos;s weather stress is applied before the agent pipeline runs.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {OPTIONS.map((opt) => {
          const isActive = value === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => onChange(opt.id)}
              className="text-left p-4 transition"
              style={{
                borderRadius: '4px',
                border: isActive ? '2px solid var(--accent)' : '1px solid var(--border)',
                background: isActive ? 'var(--accent-muted)' : 'var(--bg-card)',
                boxShadow: isActive ? '0 0 0 1px var(--accent-glow)' : 'none',
              }}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <span style={{ fontSize: '20px', lineHeight: 1 }} aria-hidden>{opt.icon}</span>
                <span
                  className="font-mono uppercase shrink-0 px-2 py-0.5"
                  style={{
                    fontSize: '8px',
                    letterSpacing: '0.1em',
                    borderRadius: '2px',
                    color: opt.tagColor,
                    border: `1px solid ${opt.tagColor}`,
                    background: opt.tagBg,
                  }}
                >
                  {opt.tag}
                </span>
              </div>
              <p
                className="font-syne font-bold"
                style={{ fontSize: '13px', color: isActive ? 'var(--navy)' : 'var(--text)' }}
              >
                {opt.label}
              </p>
              <p
                className="font-mono mt-1.5 leading-relaxed"
                style={{ fontSize: '10px', color: 'var(--muted)' }}
              >
                {opt.description}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
