/** Parse validator AgentTrace notes (legacy traces without `details`). */
export function parseValidatorNotes(notes) {
  if (!notes || typeof notes !== 'string') return null;
  const validM = notes.match(/valid=(true|false)/i);
  const errorsM = notes.match(/errors=(\d+)/);
  const warningsM = notes.match(/warnings=(\d+)/);
  const retryM = notes.match(/retry_count=(\d+)/);
  const humanM = notes.match(/human_review=(true|false)/i);
  const retryTriggeredM = notes.match(/retry_triggered=(true|false)/i);
  const violationsM = notes.match(/violations=([^\s]+)/);
  const relaxationM = notes.match(/relaxation=([\d.]+)/);
  if (!validM && !errorsM) return null;

  const errorsCount = errorsM ? Number(errorsM[1]) : 0;
  const valid = validM ? validM[1].toLowerCase() === 'true' : errorsCount === 0;

  const retryCount = retryM ? Number(retryM[1]) : 0;
  const maxRetries = 2;
  const retryTriggered = retryTriggeredM
    ? retryTriggeredM[1].toLowerCase() === 'true'
    : (!valid && retryCount > 0 && retryCount < maxRetries);

  return {
    valid,
    errors_count: errorsCount,
    warnings_count: warningsM ? Number(warningsM[1]) : 0,
    retry_count: retryCount,
    human_review: humanM ? humanM[1].toLowerCase() === 'true' : false,
    max_retries: maxRetries,
    retry_triggered: retryTriggered,
    max_retries_reached: !valid && retryCount >= maxRetries,
    reason_for_retry: violationsM
      ? violationsM[1].split(',').filter(Boolean)
      : [],
    relaxation_factor_applied: relaxationM ? Number(relaxationM[1]) : null,
    simulated: true,
    capacity_violations: valid ? 0 : null,
    time_window_violations: valid ? 0 : null,
    weather_blocked_routes: [],
    spoilage_priority_violations: valid ? 0 : null,
    driver_hours_violations: valid ? 0 : null,
  };
}

/** Merge backend `details` or fall back to notes parsing. */
export function resolveValidatorDetails(trace) {
  if (trace?.details && typeof trace.details === 'object') {
    return {
      ...trace.details,
      max_retries: trace.details.max_retries ?? 2,
      simulated: false,
    };
  }
  return parseValidatorNotes(trace?.notes || trace?.summary);
}

const CHECK_DEFS = [
  { key: 'capacity', label: 'Capacity', field: 'capacity_violations' },
  { key: 'time_window', label: 'Time windows', field: 'time_window_violations' },
  { key: 'weather', label: 'Weather routes', field: 'weather_blocked_routes', isRoutes: true },
  { key: 'spoilage', label: 'Spoilage priority', field: 'spoilage_priority_violations' },
  { key: 'driver_hours', label: 'Driver hours', field: 'driver_hours_violations' },
];

export function buildValidatorCheckRows(details) {
  if (!details) return [];

  return CHECK_DEFS.map(({ key, label, field, isRoutes }) => {
    const raw = details[field];
    if (isRoutes) {
      const routes = Array.isArray(raw) ? raw : [];
      return {
        id: key,
        label,
        status: routes.length > 0 ? 'fail' : 'pass',
        detail: routes.length > 0 ? routes.join(', ') : 'OK',
      };
    }

    if (raw === null || raw === undefined) {
      if (details.simulated && (details.errors_count ?? 0) > 0) {
        return {
          id: key,
          label,
          status: 'warn',
          detail: 'legacy trace — re-run for breakdown',
        };
      }
      return { id: key, label, status: 'pass', detail: 'OK' };
    }

    const count = Number(raw) || 0;
    return {
      id: key,
      label,
      status: count > 0 ? 'fail' : 'pass',
      detail: count > 0 ? `${count} violation(s)` : 'OK',
    };
  });
}

export function validatorSummaryLine(details, checkRows) {
  const passed = checkRows.filter((c) => c.status === 'pass').length;
  const warnings = details?.warnings_count ?? 0;
  const errors = details?.errors_count ?? 0;
  const prefix = errors > 0 ? '\u2717' : warnings > 0 ? '\u26A0' : '\u2713';
  return `${prefix} ${passed} checks passed, ${warnings} warning${warnings !== 1 ? 's' : ''}, ${errors} error${errors !== 1 ? 's' : ''}`;
}

export function validatorSummaryColor(details) {
  const errors = details?.errors_count ?? 0;
  const warnings = details?.warnings_count ?? 0;
  if (errors > 0) return 'var(--red-risk)';
  if (warnings > 0) return '#FF9800';
  return 'var(--green-ok)';
}

export function isValidatorAgent(agent) {
  const key = (agent || '').toLowerCase().replace(/_agent$/, '');
  return key === 'validator';
}

export function isLogisticsAgent(agent) {
  const key = (agent || '').toLowerCase();
  return key === 'logistics' || key === 'logistics_agent';
}
