import { resolveValidatorDetails } from '@/utils/validatorTrace';

export const MAX_VALIDATOR_RETRIES = 2;

/** "Retry 1/2" style label from validator details. */
export function validatorRetryCounterLabel(details) {
  if (!details) return null;
  const attempt = details.retry_count ?? 0;
  const max = details.max_retries ?? MAX_VALIDATOR_RETRIES;
  if (attempt <= 0 || attempt > max) return null;
  return `Retry ${attempt}/${max}`;
}

export function formatViolationTypes(reasons) {
  if (!Array.isArray(reasons) || reasons.length === 0) return 'constraints';
  return reasons
    .map((r) => String(r).replace(/_/g, ' '))
    .join(', ');
}

/** Chronological simulation steps including retry banners. */
export function buildSimulationSteps(traces) {
  if (!traces?.length) return [];

  const sorted = [...traces].sort((a, b) => {
    const ta = Date.parse(a.start_time || '') || 0;
    const tb = Date.parse(b.start_time || '') || 0;
    return ta - tb;
  });

  const steps = [];
  let logisticsAttempt = 0;

  for (let i = 0; i < sorted.length; i += 1) {
    const trace = sorted[i];
    const name = trace.agent_name || trace.agent || '';

    if (name === 'retry_prep') {
      const d = trace.details || {};
      steps.push({
        kind: 'retry_banner',
        id: `retry_prep-${steps.length}`,
        trace,
        retryCount: d.retry_count,
        relaxation: d.relaxation_factor_applied,
        demandScale: d.demand_scale,
        reasons: d.reason_for_retry || [],
      });
      continue;
    }

    if (name === 'logistics_agent') {
      logisticsAttempt += 1;
      const d = trace.details || {};
      steps.push({
        kind: 'agent',
        key: 'logistics_agent',
        id: `logistics-${logisticsAttempt}`,
        trace,
        attempt: d.attempt_number ?? logisticsAttempt,
        isRetry: Boolean(d.is_retry_run),
        details: d,
      });
      continue;
    }

    if (name === 'validator') {
      const details = resolveValidatorDetails(trace);
      steps.push({
        kind: 'agent',
        key: 'validator',
        id: `validator-${steps.length}`,
        trace,
        details,
      });
      if (details?.retry_triggered) {
        const next = sorted[i + 1];
        if (next?.agent_name !== 'retry_prep') {
          steps.push({
            kind: 'retry_banner',
            id: `retry-after-validator-${steps.length}`,
            trace,
            retryCount: details.retry_count,
            relaxation: details.relaxation_factor_applied,
            demandScale: details.demand_scale_next,
            reasons: details.reason_for_retry || [],
          });
        }
      }
      continue;
    }

    if (
      name === 'orchestrator_entry'
      || name === 'orchestrator_exit'
      || name === 'weather_agent'
      || name === 'demand_agent'
      || name === 'inventory_agent'
    ) {
      steps.push({
        kind: 'agent',
        key: name,
        id: `${name}-${steps.length}`,
        trace,
      });
    }
  }

  return steps;
}

export function hasRetryLoop(traces) {
  return (traces || []).some((t) => {
    const d = t.details || {};
    if (t.agent_name === 'retry_prep') return true;
    if (t.agent_name === 'validator' && d.retry_triggered) return true;
    return t.agent_name === 'logistics_agent' && d.is_retry_run;
  });
}
