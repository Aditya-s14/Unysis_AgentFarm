/**
 * ScenarioTypeSelect — three-up pill buttons replacing the legacy dropdown.
 * The selected pill paints saffron; unselected pills are muted on the bg.
 */
const OPTIONS = [
  { id: 'monsoon_disruption', label: 'MONSOON DISRUPTION' },
  { id: 'heat_wave',          label: 'HEAT WAVE' },
  { id: 'normal_day',         label: 'NORMAL DAY' },
];

export default function ScenarioTypeSelect({ value, onChange }) {
  return (
    <div>
      <p
        className="font-mono text-muted uppercase mb-2"
        style={{ fontSize: '0.7rem', letterSpacing: '0.1em' }}
      >
        Scenario Type
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {OPTIONS.map((opt) => {
          const active = value === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => onChange(opt.id)}
              className="font-mono text-[11px] py-3 px-3 transition tracking-wider-2"
              style={{
                background: active ? 'var(--accent)' : 'transparent',
                color: active ? '#0D1F0F' : 'var(--muted)',
                border: active
                  ? '1px solid var(--accent)'
                  : '1px solid var(--border)',
                borderRadius: '2px',
                fontWeight: active ? 600 : 400,
              }}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
