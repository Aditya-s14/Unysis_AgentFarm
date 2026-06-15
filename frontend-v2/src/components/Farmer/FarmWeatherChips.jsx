import WeatherConditionIcon from '@/components/Farmer/WeatherConditionIcon';
import {
  farmConditionFromReading,
  farmRainLabel,
  formatFarmSeverity,
  riskColor,
} from '@/utils/weatherSummary';

function WeatherChip({ icon, label, detail, background, color, border, iconBackground }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        padding: '5px 10px',
        borderRadius: 8,
        fontSize: '11px',
        fontWeight: 500,
        lineHeight: 1.2,
        background,
        color,
        border,
      }}
    >
      <span
        aria-hidden
        style={{
          width: 22,
          height: 22,
          borderRadius: 6,
          flexShrink: 0,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: iconBackground,
          fontSize: 12,
          overflow: 'hidden',
        }}
      >
        {icon}
      </span>
      <span>
        <span
          style={{
            display: 'block',
            fontSize: '9px',
            fontWeight: 600,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            opacity: 0.85,
          }}
        >
          {label}
        </span>
        <span style={{ fontSize: '11px' }}>{detail}</span>
      </span>
    </span>
  );
}

/** Compact rain + temp (+ risk) chips for farm list rows. */
export default function FarmWeatherChips({ reading }) {
  if (!reading) {
    return (
      <span className="font-mono shrink-0" style={{ fontSize: '10px', color: 'var(--muted)' }}>
        Weather unavailable
      </span>
    );
  }

  const rainMm = reading.rain_mm ?? reading.precipitation_mm;
  const rain = farmRainLabel(rainMm);
  const tempC = reading.temp_c;
  const temp = tempC != null && Number.isFinite(Number(tempC)) ? Math.round(Number(tempC)) : null;
  const isHot = temp != null && temp >= 34;
  const severity = String(reading.severity || 'normal').toLowerCase();
  const showRisk = severity && severity !== 'normal' && severity !== 'low';
  const condition = farmConditionFromReading(reading);

  if (!rain && temp == null && !showRisk) {
    return (
      <span className="font-mono shrink-0" style={{ fontSize: '10px', color: 'var(--muted)' }}>
        Weather unavailable
      </span>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2 shrink-0">
      {rain && (
        <WeatherChip
          icon={<WeatherConditionIcon condition={condition} size={14} />}
          label={rain.label}
          detail={rain.detail}
          background={rain.label === 'Dry' ? 'var(--green-muted)' : 'var(--blue-muted)'}
          color={rain.label === 'Dry' ? 'var(--forest)' : 'var(--water-blue)'}
          border={rain.label === 'Dry'
            ? '1px solid rgba(34, 160, 107, 0.22)'
            : '1px solid rgba(33, 150, 243, 0.22)'}
          iconBackground={rain.label === 'Dry' ? 'rgba(34,160,107,0.15)' : 'rgba(33,150,243,0.15)'}
        />
      )}
      {temp != null && (
        <WeatherChip
          icon={isHot ? '🔥' : '🌡'}
          label={isHot ? 'Hot' : 'Temp'}
          detail={`${temp}°C`}
          background={isHot ? 'var(--orange-muted)' : 'var(--cyan-muted)'}
          color={isHot ? 'var(--amber-warn)' : 'var(--sky-blue)'}
          border={isHot
            ? '1px solid rgba(244, 182, 62, 0.35)'
            : '1px solid rgba(74, 144, 226, 0.25)'}
          iconBackground={isHot ? 'rgba(255,193,7,0.18)' : 'rgba(74,144,226,0.15)'}
        />
      )}
      {showRisk && (
        <WeatherChip
          icon="⚠"
          label="Risk"
          detail={formatFarmSeverity(severity)}
          background="rgba(231, 76, 60, 0.08)"
          color={riskColor(severity)}
          border={`1px solid ${riskColor(severity)}`}
          iconBackground="rgba(231, 76, 60, 0.12)"
        />
      )}
    </div>
  );
}
