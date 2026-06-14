import {
  getWeatherSourceMode,
  weatherSourceTooltip,
} from '@/utils/weatherSummary';

/**
 * Compact live vs simulated weather indicator for scenario / results views.
 */
export default function WeatherSourceBanner({ weatherSummary }) {
  if (!weatherSummary || weatherSummary.unavailable) {
    return null;
  }

  const mode = getWeatherSourceMode(weatherSummary);
  const tooltip = weatherSourceTooltip(weatherSummary);

  let label;
  let color;
  let borderColor;

  if (mode === 'live') {
    label = 'Live (OpenWeather)';
    color = 'var(--green-ok)';
    borderColor = 'var(--green-ok)';
  } else if (mode === 'mixed') {
    label = 'Live + scenario overlay';
    color = 'var(--green-ok)';
    borderColor = 'var(--accent)';
  } else {
    label = 'Simulated (no API key)';
    color = '#FF9800';
    borderColor = '#FF9800';
  }

  return (
    <div
      className="font-mono text-[11px] px-3 py-2 flex items-center gap-2"
      title={tooltip}
      style={{
        border: `1px solid ${borderColor}`,
        borderRadius: '2px',
        color,
        background: 'rgba(0,0,0,0.15)',
        letterSpacing: '0.06em',
      }}
    >
      <span aria-hidden>{mode === 'synthetic' ? '⚠' : '🌤'}</span>
      <span className="uppercase tracking-wider-2">{label}</span>
    </div>
  );
}
