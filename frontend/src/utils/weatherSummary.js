const SYNTHETIC_TOOLTIP =
  'Using synthetic weather because OpenWeather API key is not configured or API calls failed. '
  + 'Scenario effects are applied from the selected scenario type.';

/** Normalize API `source` / `weather_source` onto one field. */
export function normalizeWeatherSource(summary) {
  if (!summary || typeof summary !== 'object') return '';
  return String(summary.source || summary.weather_source || '').toLowerCase();
}

/**
 * Resolve weather panel payload from cached scenario response only.
 * Returns `{ unavailable: true }` when `weather_summary` is absent — no invented copy.
 */
export function resolveWeatherPanel(cached) {
  if (!cached) return null;

  if (!cached.weather_summary || typeof cached.weather_summary !== 'object') {
    return { unavailable: true };
  }

  const ws = { ...cached.weather_summary };
  const src = normalizeWeatherSource(ws);
  if (src) {
    ws.source = src;
    ws.weather_source = src;
  }
  return ws;
}

/** live | stale | synthetic | mixed */
export function getWeatherSourceMode(data) {
  if (!data || data.unavailable) return 'unavailable';
  const src = normalizeWeatherSource(data);
  if (src === 'mixed') return 'mixed';
  if (src === 'openweather' && data.scenario_modifier_applied) return 'mixed';
  if (src === 'openweather') return 'live';
  if (src === 'stale_cache' || data.stale_reading) return 'stale';
  if (src === 'synthetic_fallback') return 'synthetic';
  return src ? 'synthetic' : 'unavailable';
}

export function weatherSourceTooltip(data) {
  const mode = getWeatherSourceMode(data);
  if (mode === 'live') {
    const scenario = (data.scenario_type || '').toLowerCase();
    if (scenario === 'live_weather') {
      return 'Per-farm OpenWeather readings drive risk, shelf life, and routing — no scripted overlay.';
    }
    return 'Temperature and rainfall from OpenWeatherMap current + forecast APIs.';
  }
  if (mode === 'mixed') {
    const disclaimer = data.weather_disclaimer ? ` ${data.weather_disclaimer}` : '';
    return (
      'Live OpenWeather readings with scenario overlay applied for the selected scenario type. '
      + (data.scenario_adjustment_label || '')
      + disclaimer
    );
  }
  if (mode === 'stale') {
    return data.weather_disclaimer
      || "Couldn't fetch the current weather update; showing the most recently fetched reading.";
  }
  if (mode === 'synthetic') {
    return data.synthetic_reason || SYNTHETIC_TOOLTIP;
  }
  return null;
}

/**
 * Primary condition line from API fields (no hardcoded scenario sentences).
 */
export function weatherHeadline(data) {
  if (!data || data.unavailable) return null;

  const src = normalizeWeatherSource(data);
  const condition = conditionLabel(data.condition);
  const scenarioRaw = data.scenario_type || '';
  const scenarioLabel = scenarioRaw ? scenarioRaw.replace(/_/g, ' ') : '—';

  if (src === 'openweather') {
    if (scenarioRaw === 'live_weather') {
      return `Live weather: ${condition}`;
    }
    return `Live: ${condition}`;
  }
  if (src === 'stale_cache') {
    return `Cached weather: ${condition}`;
  }
  if (src === 'synthetic_fallback') {
    if (data.fallback_mode === 'live_weather' || data.effective_scenario_type === 'live_weather') {
      return 'Live weather fallback (OpenWeather unavailable): mild baseline, live risk rules';
    }
    return `Simulated (no API key): ${scenarioLabel} effects applied`;
  }
  if (src === 'mixed') {
    return `Live: ${condition} (${scenarioLabel} overlay)`;
  }

  if (data.condition != null && data.condition !== '') {
    return condition;
  }
  return null;
}

export function formatRainfallDisplay(data) {
  if (!data || data.unavailable) return '—';
  const mm = data.rainfall_mm;
  if (mm != null && Number(mm) > 0) {
    return `${Number(mm)} mm (24h)`;
  }
  const prob = data.rainfall_probability_pct;
  if (prob != null) {
    return `${Math.round(Number(prob))}% prob.`;
  }
  if (mm != null) return `${Number(mm)} mm`;
  return '—';
}

export function conditionLabel(condition) {
  if (condition == null || condition === '') return '—';
  const map = {
    sunny: 'Sunny',
    rain: 'Rain',
    heat_wave: 'Heat wave',
    live_weather: 'Live conditions',
  };
  return map[condition] || String(condition);
}

export function formatReadingAge(isoTimestamp) {
  if (!isoTimestamp) return null;
  const fetched = new Date(isoTimestamp);
  if (Number.isNaN(fetched.getTime())) return null;
  const minutes = Math.max(0, Math.round((Date.now() - fetched.getTime()) / 60000));
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} hr ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}

export function riskColor(level) {
  if (level == null || level === '') return 'var(--muted)';
  const l = String(level).toLowerCase();
  if (l === 'high') return 'var(--red-risk)';
  if (l === 'moderate') return '#FF9800';
  return 'var(--green-ok)';
}
