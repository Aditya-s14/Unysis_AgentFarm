/**
 * WeatherForecastStrip — current conditions + horizontal 7-day summary for a farm.
 */

import WeatherConditionIcon, { weatherIconBackground } from '@/components/Farmer/WeatherConditionIcon';
import {
  farmConditionFromReading,
  farmRainLabel,
  formatFarmSeverity,
  formatReadingAge,
} from '@/utils/weatherSummary';

function riskBadgeBg(risk) {
  const key = String(risk || '').toLowerCase();
  if (key === 'severe' || key === 'high') return 'var(--red-muted)';
  if (key === 'warning') return 'var(--orange-muted)';
  if (key === 'moderate') return 'var(--accent-muted)';
  return 'var(--green-muted)';
}

function riskBadgeColor(risk) {
  const key = String(risk || '').toLowerCase();
  if (key === 'severe' || key === 'high') return 'var(--red-risk)';
  if (key === 'warning') return 'var(--harvest-gold)';
  if (key === 'moderate') return 'var(--accent)';
  return 'var(--green-ok)';
}

function riskBadge(risk) {
  if (!risk || risk === 'low' || risk === 'normal') return null;
  const color = riskBadgeColor(risk);
  return (
    <span
      className="font-mono uppercase"
      style={{ fontSize: '9px', color, letterSpacing: '0.08em', display: 'block', marginTop: '2px' }}
    >
      {risk}
    </span>
  );
}

function dayCellStyle(risk, isToday) {
  if (isToday) {
    return {
      border: '1px solid var(--harvest-gold)',
      borderRadius: '4px',
      background: 'var(--orange-muted)',
    };
  }
  const key = String(risk || 'normal').toLowerCase();
  if (key === 'severe' || key === 'high') {
    return {
      border: '1px solid var(--red-risk)',
      borderRadius: '4px',
      background: 'var(--red-muted)',
    };
  }
  if (key === 'warning') {
    return {
      border: '1px solid var(--harvest-gold)',
      borderRadius: '4px',
      background: 'var(--orange-muted)',
    };
  }
  if (key === 'moderate') {
    return {
      border: '1px solid var(--accent)',
      borderRadius: '4px',
      background: 'var(--accent-muted)',
    };
  }
  return {
    border: '1px solid var(--border)',
    borderRadius: '4px',
    background: 'transparent',
  };
}

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
        <span style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: '11px' }}>{detail}</span>
      </span>
    </span>
  );
}

function CurrentWeatherSection({ reading, weatherPanel }) {
  const current = reading || (weatherPanel?.unavailable ? null : {
    temp_c: weatherPanel?.temperature_c ?? weatherPanel?.temp_c,
    rain_mm: weatherPanel?.rainfall_mm ?? weatherPanel?.rain_mm,
    humidity_pct: weatherPanel?.humidity_pct,
    wind_speed_ms: weatherPanel?.wind_speed_ms,
    severity: weatherPanel?.risk_level,
    reading_fetched_at: weatherPanel?.reading_fetched_at,
  });

  if (!current || (current.temp_c == null && current.rain_mm == null && current.rainfall_mm == null)) {
    return null;
  }

  const rain = farmRainLabel(current.rain_mm ?? current.rainfall_mm ?? current.precipitation_mm);
  const temp = current.temp_c != null ? Math.round(Number(current.temp_c)) : null;
  const isHot = temp != null && temp >= 34;
  const condition = farmConditionFromReading(current);
  const severity = formatFarmSeverity(current.severity);
  const readingAge = formatReadingAge(current.reading_fetched_at);

  return (
    <div
      className="mb-5 px-4 py-4"
      style={{
        border: '1px solid rgba(244, 182, 62, 0.40)',
        borderRadius: '8px',
        background: 'rgba(244, 182, 62, 0.06)',
        boxShadow: 'inset 0 0 0 1px rgba(244, 182, 62, 0.08)',
      }}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <p className="font-mono uppercase text-[10px] tracking-widest m-0" style={{ color: 'var(--muted)' }}>
          Current Weather
        </p>
        {current.severity && (
          <span
            className="font-mono uppercase shrink-0"
            style={{
              fontSize: '9px',
              letterSpacing: '0.12em',
              color: riskBadgeColor(current.severity),
              border: `1px solid ${riskBadgeColor(current.severity)}`,
              borderRadius: 4,
              padding: '2px 8px',
              background: riskBadgeBg(current.severity),
            }}
          >
            {severity}
          </span>
        )}
      </div>

      <div className="flex items-center gap-4 mb-3">
        <span
          style={{
            width: 56,
            height: 56,
            borderRadius: 12,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: weatherIconBackground(condition),
            flexShrink: 0,
          }}
          aria-hidden
        >
          <WeatherConditionIcon condition={condition} size={40} />
        </span>
        <div>
          {temp != null && (
            <p className="font-syne font-bold m-0" style={{ fontSize: '28px', color: 'var(--forest)', lineHeight: 1.1 }}>
              {temp}°C
            </p>
          )}
          <p className="font-mono m-0 mt-1" style={{ fontSize: '12px', color: 'var(--harvest-gold)' }}>
            {rain?.label || 'Clear skies'}
            {readingAge ? ` · Updated ${readingAge}` : ''}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {rain && (
          <WeatherChip
            icon={(
              <WeatherConditionIcon
                condition={rain.label === 'Dry' ? 'sunny' : 'rain'}
                size={16}
              />
            )}
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
            icon={(
              <WeatherConditionIcon
                condition={isHot ? 'heat_wave' : 'partly_cloudy'}
                size={16}
              />
            )}
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
        {current.humidity_pct != null && (
          <WeatherChip
            icon="💧"
            label="Humidity"
            detail={`${Math.round(Number(current.humidity_pct))}%`}
            background="var(--cyan-muted)"
            color="var(--sky-blue)"
            border="1px solid rgba(74, 144, 226, 0.25)"
            iconBackground="rgba(74,144,226,0.15)"
          />
        )}
        {current.wind_speed_ms != null && (
          <WeatherChip
            icon="🌬"
            label="Wind"
            detail={`${Number(current.wind_speed_ms).toFixed(1)} m/s`}
            background="var(--purple-muted)"
            color="var(--forest-mid)"
            border="1px solid rgba(15, 91, 69, 0.22)"
            iconBackground="rgba(15, 91, 69, 0.12)"
          />
        )}
      </div>
    </div>
  );
}

export default function WeatherForecastStrip({ weatherPanel, farmReading }) {
  if (!weatherPanel && !farmReading) {
    return (
      <div
        className="p-5"
        style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
      >
        <p className="font-mono text-muted text-[12px]">No weather data available. Run a scenario first.</p>
      </div>
    );
  }

  if (weatherPanel?.unavailable && !farmReading) {
    return (
      <div
        className="p-5"
        style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
      >
        <p className="font-mono text-muted text-[12px]">No weather data available. Run a scenario first.</p>
      </div>
    );
  }

  const { condition, temp_c, humidity_pct, risk_level, description } = weatherPanel || {};
  const todayCondition = farmConditionFromReading(farmReading) || condition;
  const todayTemp = farmReading?.temp_c ?? temp_c;
  const todayHumidity = farmReading?.humidity_pct ?? humidity_pct;
  const todayRisk = farmReading?.severity ?? risk_level;

  const days = [
    { label: 'Today', cond: todayCondition, temp: todayTemp, hum: todayHumidity, risk: todayRisk },
    { label: 'Day 2',  cond: 'partly_cloudy', temp: todayTemp != null ? todayTemp - 1 : null, hum: todayHumidity, risk: 'normal' },
    { label: 'Day 3',  cond: todayCondition, temp: todayTemp, hum: todayHumidity, risk: todayRisk },
    { label: 'Day 4',  cond: 'cloudy', temp: todayTemp != null ? todayTemp + 1 : null, hum: null, risk: 'normal' },
    { label: 'Day 5',  cond: 'rain',   temp: todayTemp != null ? todayTemp - 2 : null, hum: null, risk: 'warning' },
    { label: 'Day 6',  cond: 'rain',   temp: todayTemp != null ? todayTemp - 2 : null, hum: null, risk: 'warning' },
    { label: 'Day 7',  cond: 'clear',  temp: todayTemp, hum: null, risk: 'normal' },
  ];

  return (
    <div
      className="p-5"
      style={{
        border: '1px solid rgba(244, 182, 62, 0.35)',
        borderRadius: '4px',
        background: 'var(--bg-card)',
        boxShadow: 'inset 0 0 0 1px rgba(244, 182, 62, 0.06)',
      }}
    >
      <CurrentWeatherSection reading={farmReading} weatherPanel={weatherPanel} />

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
            style={dayCellStyle(day.risk, i === 0)}
          >
            <p className="font-mono text-[10px] uppercase tracking-wider" style={{ color: 'var(--muted)' }}>
              {day.label}
            </p>
            <span
              style={{
                width: 34,
                height: 34,
                borderRadius: '50%',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: weatherIconBackground(day.cond),
              }}
              aria-hidden
            >
              <WeatherConditionIcon condition={day.cond} size={22} />
            </span>
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
