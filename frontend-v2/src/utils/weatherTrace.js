export function isWeatherAgent(agent) {
  const key = (agent || '').toLowerCase().replace(/_agent$/, '');
  return key === 'weather';
}

export function parseWeatherTraceNotes(notes) {
  if (!notes || typeof notes !== 'string') return null;
  const srcM = notes.match(/weather_source=([a-z_]+)/i);
  const modM = notes.match(/scenario_modifier_applied=(true|false)/i);
  if (!srcM && !modM) return null;
  return {
    weather_source: srcM ? srcM[1] : 'unknown',
    scenario_modifier_applied: modM ? modM[1].toLowerCase() === 'true' : null,
  };
}

export function weatherSourceLabel(source) {
  if (source === 'openweather') return 'OpenWeather API (live)';
  if (source === 'mixed') return 'OpenWeather + scenario overlay';
  if (source === 'synthetic_fallback') return 'Synthetic fallback';
  return source || 'unknown';
}
