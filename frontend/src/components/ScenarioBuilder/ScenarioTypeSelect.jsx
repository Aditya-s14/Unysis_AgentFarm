/**
 * ScenarioTypeSelect — pill buttons for disruption templates and the retry demo.
 */
const OPTIONS = [
  {
    id: 'monsoon_disruption',
    label: 'MONSOON DISRUPTION',
    description:
      'Heavy rain in coastal / Western Ghats farms; shelf life −20%; affected road legs ×1.3 travel time.',
  },
  {
    id: 'heat_wave',
    label: 'HEAT WAVE',
    description:
      'Temperatures ≥39°C; shelf life −40%; morning-delivery bias on urgent farm→mandi routes.',
  },
  {
    id: 'normal_day',
    label: 'NORMAL DAY',
    description:
      'Baseline weather and routing; no scenario stress overlays on shelf life or distances.',
  },
  {
    id: 'live_weather',
    label: 'LIVE WEATHER',
    description:
      'Uses OpenWeather at each farm (no scripted rain/temp overlay). Shelf life and routing stress follow observed rain and temperature.',
  },
  {
    id: 'capacity_stress',
    label: 'VALIDATOR RETRY DEMO',
    description:
      'Uses 3 undersized trucks (400 kg each) to trigger capacity failures and the retry loop. Weather = Normal Day.',
  },
];

export default function ScenarioTypeSelect({ value, onChange }) {
  const active = OPTIONS.find((o) => o.id === value) || OPTIONS[0];

  return (
    <div>
      <p
        className="font-mono text-muted uppercase mb-2"
        style={{ fontSize: '0.7rem', letterSpacing: '0.1em' }}
      >
        Scenario Type
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-2">
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
                color: isActive ? '#0D1F0F' : 'var(--muted)',
                border: isActive
                  ? '1px solid var(--accent)'
                  : '1px solid var(--border)',
                borderRadius: '2px',
                fontWeight: isActive ? 600 : 400,
              }}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
      <p
        className="font-mono text-muted mt-3 leading-relaxed"
        style={{ fontSize: '11px' }}
      >
        {active.description}
      </p>
    </div>
  );
}
