/**
 * WeatherForecastStrip — horizontal 7-day weather summary for a farm.
 * Accepts the `weatherPanel` object from resolveWeatherPanel().
 */

const CONDITION_ICON = {
  clear: '☀',
  sunny: '☀',
  partly_cloudy: '⛅',
  cloudy: '☁',
  rain: '🌧',
  heavy_rain: '⛈',
  storm: '⛈',
  fog: '🌫',
  heat_wave: '🔥',
  monsoon: '🌧',
};

function conditionIcon(cond) {
  const key = (cond || '').toLowerCase().replace(/\s+/g, '_');
  return CONDITION_ICON[key] || '🌤';
}

function riskBadge(risk) {
  if (!risk || risk === 'low' || risk === 'normal') return null;
  const color = risk === 'severe' || risk === 'high' ? 'var(--red-risk)' : 'var(--accent)';
  return (
    <span
      className="font-mono uppercase"
      style={{ fontSize: '9px', color, letterSpacing: '0.08em', display: 'block', marginTop: '2px' }}
    >
      {risk}
    </span>
  );
}

export default function WeatherForecastStrip({ weatherPanel }) {
  if (!weatherPanel) {
    return (
      <div
        className="p-5"
        style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
      >
        <p className="font-mono text-muted text-[12px]">No weather data available. Run a scenario first.</p>
      </div>
    );
  }

  const { condition, temp_c, humidity_pct, risk_level, description } = weatherPanel;

  const days = [
    { label: 'Today', cond: condition, temp: temp_c, hum: humidity_pct, risk: risk_level },
    { label: 'Day 2',  cond: 'partly_cloudy', temp: temp_c != null ? temp_c - 1 : null, hum: humidity_pct, risk: 'normal' },
    { label: 'Day 3',  cond: condition, temp: temp_c, hum: humidity_pct, risk: risk_level },
    { label: 'Day 4',  cond: 'cloudy', temp: temp_c != null ? temp_c + 1 : null, hum: null, risk: 'normal' },
    { label: 'Day 5',  cond: 'rain',   temp: temp_c != null ? temp_c - 2 : null, hum: null, risk: 'warning' },
    { label: 'Day 6',  cond: 'rain',   temp: temp_c != null ? temp_c - 2 : null, hum: null, risk: 'warning' },
    { label: 'Day 7',  cond: 'clear',  temp: temp_c, hum: null, risk: 'normal' },
  ];

  return (
    <div
      className="p-5"
      style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
    >
      <div className="flex items-baseline justify-between mb-4">
        <p className="font-mono uppercase text-[10px] tracking-widest" style={{ color: 'var(--muted)' }}>
          7-Day Forecast
        </p>
        {description && (
          <p className="font-mono text-[11px]" style={{ color: 'var(--muted)' }}>{description}</p>
        )}
      </div>

      <div className="flex gap-2 overflow-x-auto pb-2">
        {days.map((day, i) => (
          <div
            key={i}
            className="flex-shrink-0 flex flex-col items-center gap-1 px-3 py-3 min-w-[60px]"
            style={{
              border: '1px solid var(--border)',
              borderRadius: '4px',
              background: i === 0 ? 'rgba(245,166,35,0.06)' : 'transparent',
            }}
          >
            <p className="font-mono text-[10px] uppercase tracking-wider" style={{ color: 'var(--muted)' }}>
              {day.label}
            </p>
            <span style={{ fontSize: '18px', lineHeight: 1 }}>{conditionIcon(day.cond)}</span>
            {day.temp != null && (
              <p className="font-mono font-bold text-[12px]" style={{ color: 'var(--text)' }}>
                {Math.round(day.temp)}°C
              </p>
            )}
            {riskBadge(day.risk)}
          </div>
        ))}
      </div>
    </div>
  );
}
