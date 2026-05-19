import {
  conditionLabel,
  formatRainfallDisplay,
  getWeatherSourceMode,
  riskColor,
  weatherHeadline,
  weatherSourceTooltip,
} from '@/utils/weatherSummary';

function SourceBadge({ children, color, borderColor, title }) {
  return (
    <span
      className="font-mono uppercase inline-flex items-center gap-1"
      title={title}
      style={{
        fontSize: '9px',
        letterSpacing: '0.1em',
        color,
        border: `1px solid ${borderColor || color}`,
        borderRadius: '2px',
        padding: '3px 8px',
        cursor: title ? 'help' : 'default',
      }}
    >
      {children}
    </span>
  );
}

function SourceBadges({ data }) {
  const mode = getWeatherSourceMode(data);
  const tooltip = weatherSourceTooltip(data);

  if (mode === 'live') {
    return (
      <SourceBadge color="var(--green-ok)" borderColor="var(--green-ok)" title={tooltip}>
        Live (OpenWeather API)
      </SourceBadge>
    );
  }

  if (mode === 'mixed') {
    const adj = data.scenario_adjustment_label || 'Scenario overlay';
    return (
      <div className="flex flex-wrap gap-2">
        <SourceBadge color="var(--green-ok)" borderColor="var(--green-ok)" title={tooltip}>
          Live Weather
        </SourceBadge>
        <SourceBadge color="var(--accent)" borderColor="var(--accent)" title={tooltip}>
          Scenario Adjustment ({adj})
        </SourceBadge>
      </div>
    );
  }

  if (mode === 'synthetic') {
    return (
      <SourceBadge color="#FF9800" borderColor="#FF9800" title={tooltip}>
        Simulated Weather
      </SourceBadge>
    );
  }

  return null;
}

/**
 * Compact weather risk card for the Overview tab.
 */
export default function WeatherRiskPanel({ data }) {
  if (!data) return null;

  if (data.unavailable) {
    return (
      <div
        className="px-4 py-4"
        style={{
          border: '1px solid var(--border)',
          borderRadius: '4px',
          background: 'var(--bg-card)',
        }}
      >
        <h2
          className="font-syne font-bold uppercase text-paper tracking-wider m-0"
          style={{ fontSize: '13px', letterSpacing: '0.08em' }}
        >
          Weather risk
        </h2>
        <p className="font-mono text-muted mt-3 m-0" style={{ fontSize: '12px' }}>
          Weather data unavailable
        </p>
      </div>
    );
  }

  const {
    condition,
    temperature_c: temp,
    temperature_c_base: tempBase,
    rainfall_mm_base: rainBase,
    rainfall_probability_pct: rainProb,
    humidity_pct: humidity,
    wind_speed_ms: windMs,
    risk_level: riskLevel,
    affected_farms: affectedFarms = [],
    transport_advisory: advisory,
    recommended_action: action,
  } = data;

  const mode = getWeatherSourceMode(data);
  const headline = weatherHeadline(data);
  const showBaseValues = mode === 'mixed' && (tempBase != null || rainBase != null);
  const rainDisplay = formatRainfallDisplay(data);
  const rainBaseDisplay = rainBase != null ? `${Number(rainBase)} mm (24h)` : null;

  const affectedPreview = affectedFarms.slice(0, 4);
  const affectedMore = affectedFarms.length - affectedPreview.length;

  return (
    <div
      className="px-4 py-4"
      style={{
        border: '1px solid rgba(245, 166, 35, 0.45)',
        borderRadius: '4px',
        background: 'rgba(245, 166, 35, 0.04)',
        boxShadow: 'inset 0 0 0 1px rgba(245, 166, 35, 0.08)',
      }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
        <h2
          className="font-syne font-bold uppercase text-paper tracking-wider"
          style={{ fontSize: '13px', letterSpacing: '0.08em' }}
        >
          Weather risk
        </h2>
        <span
          className="font-mono uppercase shrink-0"
          style={{
            fontSize: '10px',
            letterSpacing: '0.12em',
            color: riskColor(riskLevel),
            border: `1px solid ${riskColor(riskLevel)}`,
            borderRadius: '2px',
            padding: '2px 8px',
          }}
        >
          {riskLevel != null && riskLevel !== '' ? `${riskLevel} risk` : 'N/A'}
        </span>
      </div>

      <div className="mb-3">
        <SourceBadges data={data} />
      </div>

      {headline ? (
        <p
          className="font-mono mb-3 font-bold text-paper"
          style={{ fontSize: '12px', lineHeight: 1.5 }}
        >
          {headline}
        </p>
      ) : (
        <p className="font-mono mb-3 m-0" style={{ fontSize: '12px', color: 'var(--muted)' }}>
          Weather data unavailable
        </p>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-3">
        <WeatherStat label="Condition" value={conditionLabel(condition)} />
        <WeatherStat
          label="Temperature"
          value={temp != null ? `${temp}°C` : '—'}
          subValue={showBaseValues && tempBase != null ? `API base ${tempBase}°C` : null}
        />
        <WeatherStat
          label="Rainfall"
          value={rainDisplay}
          subValue={showBaseValues && rainBaseDisplay ? `API base ${rainBaseDisplay}` : null}
        />
        {humidity != null ? (
          <WeatherStat label="Humidity" value={`${Math.round(humidity)}%`} />
        ) : (
          <WeatherStat label="Humidity" value="—" />
        )}
        {windMs != null ? (
          <WeatherStat label="Wind" value={`${windMs} m/s`} />
        ) : (
          <WeatherStat label="Wind" value="—" />
        )}
        <WeatherStat
          label="Risk"
          value={riskLevel != null && riskLevel !== '' ? riskLevel : '—'}
          valueColor={riskColor(riskLevel)}
        />
      </div>

      {showBaseValues && (
        <p
          className="font-mono text-muted mb-3"
          style={{ fontSize: '10px', letterSpacing: '0.06em' }}
        >
          Adjusted values shown above; API base readings before scenario overlay.
        </p>
      )}

      {affectedFarms.length > 0 && (
        <div className="mb-3">
          <p className="font-mono text-muted uppercase mb-1" style={{ fontSize: '9px', letterSpacing: '0.1em' }}>
            Affected farms
          </p>
          <p className="font-mono text-paper m-0" style={{ fontSize: '11px', lineHeight: 1.5 }}>
            {affectedPreview.join(' · ')}
            {affectedMore > 0 && (
              <span className="text-muted"> · +{affectedMore} more</span>
            )}
          </p>
        </div>
      )}

      <div className="space-y-2 pt-2" style={{ borderTop: '1px solid var(--border)' }}>
        <AdvisoryRow icon="→" label="Transport" text={advisory} />
        <AdvisoryRow icon="✓" label="Action" text={action} />
      </div>
    </div>
  );
}

function WeatherStat({ label, value, subValue, valueColor }) {
  return (
    <div>
      <p className="font-mono text-muted uppercase m-0" style={{ fontSize: '9px', letterSpacing: '0.1em' }}>
        {label}
      </p>
      <p
        className="font-syne font-bold text-paper m-0 mt-0.5"
        style={{ fontSize: '14px', color: valueColor || 'var(--text)' }}
      >
        {value}
      </p>
      {subValue && (
        <p className="font-mono text-muted m-0 mt-0.5" style={{ fontSize: '9px' }}>
          {subValue}
        </p>
      )}
    </div>
  );
}

function AdvisoryRow({ icon, label, text, accent }) {
  if (text == null || text === '') return null;
  return (
    <div className="flex gap-2">
      <span
        className="font-mono shrink-0"
        style={{ fontSize: '11px', color: accent ? 'var(--accent)' : 'var(--muted)' }}
      >
        {icon}
      </span>
      <p className="font-mono m-0" style={{ fontSize: '11px', lineHeight: 1.5, color: 'var(--text)' }}>
        <span className="text-muted uppercase" style={{ fontSize: '9px', letterSpacing: '0.08em' }}>
          {label}:{' '}
        </span>
        {text}
      </p>
    </div>
  );
}
