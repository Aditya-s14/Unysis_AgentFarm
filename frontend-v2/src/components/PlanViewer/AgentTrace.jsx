import { useState } from 'react';
import { formatDuration } from '@/utils/formatters';
import {
  formatViolationTypes,
  validatorRetryCounterLabel,
} from '@/utils/retryLoopTrace';
import { WARN } from '@/utils/uiChars';
import {
  buildValidatorCheckRows,
  isLogisticsAgent,
  isValidatorAgent,
  resolveValidatorDetails,
  validatorSummaryColor,
  validatorSummaryLine,
} from '@/utils/validatorTrace';
import {
  isWeatherAgent,
  parseWeatherTraceNotes,
  weatherSourceLabel,
} from '@/utils/weatherTrace';

/**
 * AgentTrace — vertical timeline of per-agent reasoning steps.
 *
 * Backend trace shape (per item):
 *   { agent_name, start_time, end_time, tools_used, notes, token_count,
 *     execution_type?, details? }
 */
const AGENT_COLOR = {
  orchestrator: 'var(--accent)',
  weather: '#2196F3',
  demand: 'var(--harvest-gold)',
  inventory: 'var(--green-ok)',
  logistics: '#0F5B45',
  validator: 'var(--muted)',
};

const DETERMINISTIC_AGENTS = new Set(['logistics', 'logistics_agent', 'validator']);

const CHECK_STATUS_STYLE = {
  pass: { color: 'var(--green-ok)', icon: '✓' },
  fail: { color: 'var(--red-risk)', icon: '✗' },
  warn: { color: 'var(--harvest-gold)', icon: WARN },
};

function colorForAgent(name) {
  const key = (name || '').toLowerCase().replace(/_agent$/, '');
  return AGENT_COLOR[key] || 'var(--accent)';
}

function isDeterministicAgent(agent) {
  const key = (agent || '').toLowerCase().replace(/_agent$/, '');
  return DETERMINISTIC_AGENTS.has(key) || DETERMINISTIC_AGENTS.has(agent?.toLowerCase());
}

function formatExecutionLabel(step) {
  if (step.execution_type) return step.execution_type;
  if (isWeatherAgent(step.agent)) {
    return 'deterministic weather engine';
  }
  if (isValidatorAgent(step.agent)) {
    return 'deterministic validation engine';
  }
  if (isDeterministicAgent(step.agent) && (step.token_count === 0 || step.token_count == null)) {
    return '0 tokens – deterministic tool';
  }
  if (step.token_count == null) return '—';
  return `${step.token_count} tok`;
}

export default function AgentTrace({ traces }) {
  const raw = Array.isArray(traces)
    ? traces
    : Array.isArray(traces?.agent_steps)
      ? traces.agent_steps
      : [];

  const list = raw.map(normaliseStep);

  return (
    <div
      className="bg-card"
      style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
    >
      <div
        className="px-5 py-3 flex items-baseline justify-between"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <h3
          className="font-syne font-bold uppercase text-paper tracking-wider-2"
          style={{ fontSize: '14px' }}
        >
          ▸ Agent Reasoning Trace
        </h3>
        <span className="font-mono text-muted text-[11px] tracking-wider">
          {list.length} steps
        </span>
      </div>

      {list.length === 0 ? (
        <p className="px-5 py-6 font-mono text-muted text-[12px]">
          No traces yet — run a scenario.
        </p>
      ) : (
        <ol className="relative px-5 py-4">
          {list.map((step, idx) => (
            <TraceStep key={idx} step={step} isLast={idx === list.length - 1} />
          ))}
        </ol>
      )}
    </div>
  );
}

function normaliseStep(t) {
  if (!t) {
    return {
      agent: 'unknown',
      duration_ms: null,
      summary: '',
      tool_calls: [],
      token_count: null,
      execution_type: null,
      details: null,
    };
  }
  const agent = t.agent || t.agent_name || 'unknown';
  const summary = t.summary || t.notes || '';
  const rawTokens = t.token_count ?? t.tokenCount;
  const tokenCount = rawTokens === undefined ? null : rawTokens;

  let duration = t.duration_ms;
  if (duration == null && t.start_time && t.end_time) {
    const s = Date.parse(t.start_time);
    const e = Date.parse(t.end_time);
    if (!Number.isNaN(s) && !Number.isNaN(e)) duration = Math.max(0, e - s);
  }

  let toolCalls = [];
  if (Array.isArray(t.tool_calls)) {
    toolCalls = t.tool_calls;
  } else if (Array.isArray(t.tools_used)) {
    toolCalls = t.tools_used.map((tool) =>
      typeof tool === 'string' ? { tool, duration_ms: null } : tool,
    );
  }

  return {
    agent,
    duration_ms: duration,
    token_count: tokenCount,
    summary,
    tool_calls: toolCalls,
    execution_type: t.execution_type || null,
    details: t.details || null,
    rawTrace: t,
  };
}

function ToolChips({ toolCalls }) {
  if (!toolCalls?.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {toolCalls.map((tc, i) => {
        const label = tc.tool || tc.name || String(tc);
        return (
          <span
            key={`${label}-${i}`}
            className="font-mono uppercase"
            style={{
              fontSize: '9px',
              letterSpacing: '0.08em',
              color: 'var(--accent)',
              border: '1px solid var(--harvest-gold)',
              background: 'var(--orange-selected)',
              borderRadius: '2px',
              padding: '2px 6px',
            }}
          >
            {label}
          </span>
        );
      })}
    </div>
  );
}

function WeatherTraceBody({ step }) {
  const parsed = parseWeatherTraceNotes(step.summary);
  if (!parsed) {
    return step.summary ? (
      <p className="font-mono mt-2 text-[11.5px] leading-relaxed" style={{ color: 'var(--muted)' }}>
        {step.summary}
      </p>
    ) : null;
  }

  return (
    <div className="mt-3 space-y-2">
      <p className="font-mono text-[11px]" style={{ color: 'var(--text)' }}>
        <span style={{ color: 'var(--accent)' }}>Source: </span>
        {weatherSourceLabel(parsed.weather_source)}
      </p>
      {parsed.scenario_modifier_applied != null && (
        <p className="font-mono text-[11px]" style={{ color: 'var(--muted)' }}>
          scenario_modifier_applied={String(parsed.scenario_modifier_applied)}
        </p>
      )}
      {step.summary && (
        <p className="font-mono text-[10.5px] leading-relaxed" style={{ color: 'var(--muted)' }}>
          {step.summary}
        </p>
      )}
      <ToolChips toolCalls={step.tool_calls} />
    </div>
  );
}

function ValidatorTraceBody({ step }) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const details = resolveValidatorDetails(step.rawTrace || step);
  const checkRows = buildValidatorCheckRows(details);

  if (!details) {
    return step.summary ? (
      <p className="font-mono mt-2 text-[11.5px] leading-relaxed" style={{ color: 'var(--muted)' }}>
        {step.summary}
      </p>
    ) : null;
  }

  const maxRetries = details.max_retries ?? 2;
  const retryLabel = validatorRetryCounterLabel(details);
  const summaryColor = validatorSummaryColor(details);
  const summaryText = validatorSummaryLine(details, checkRows);

  return (
    <div className="mt-3 space-y-2">
      <p className="font-mono text-[11.5px] font-bold" style={{ color: summaryColor }}>
        {summaryText}
      </p>

      {details.simulated && (
        <p className="font-mono text-[10px] uppercase" style={{ color: 'var(--muted)', letterSpacing: '0.1em' }}>
          Simulated validation breakdown (legacy trace — re-run scenario for live counts)
        </p>
      )}

      {details.retry_triggered && (
        <div
          className="font-mono space-y-1.5 p-2.5"
          style={{
            fontSize: '11px',
            lineHeight: 1.5,
            color: 'var(--red-risk)',
            border: '1px solid rgba(229, 57, 53, 0.45)',
            borderRadius: '2px',
            background: 'rgba(229, 57, 53, 0.06)',
          }}
        >
          <p className="m-0 font-bold">
            {WARN} Validation failed – retrying with relaxed constraints
          </p>
          {retryLabel && (
            <p className="m-0 uppercase" style={{ fontSize: '10px', letterSpacing: '0.12em' }}>
              {retryLabel}
              {details.relaxation_factor_applied != null && (
                <span className="text-muted normal-case">
                  {' '}
                  · relaxation ×{details.relaxation_factor_applied}
                  {details.demand_scale_next != null && ` (demand ${details.demand_scale_next})`}
                </span>
              )}
            </p>
          )}
          {(details.reason_for_retry?.length ?? 0) > 0 && (
            <p className="m-0 text-muted" style={{ fontSize: '10px' }}>
              Violations: {formatViolationTypes(details.reason_for_retry)}
            </p>
          )}
        </div>
      )}

      {details.max_retries_reached && !details.valid && (
        <p
          className="font-mono m-0 font-bold"
          style={{ fontSize: '11px', lineHeight: 1.5, color: 'var(--red-risk)' }}
        >
          ❌ Plan requires human review after {maxRetries} failed validation attempts
        </p>
      )}

      <ToolChips toolCalls={step.tool_calls} />

      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setDetailsOpen((v) => !v);
        }}
        className="font-mono uppercase tracking-wider"
        style={{ fontSize: '9px', letterSpacing: '0.16em', color: 'var(--accent)' }}
        aria-expanded={detailsOpen}
      >
        {detailsOpen ? '▾' : '▶'} Validation details
      </button>

      {detailsOpen && (
        <ul
          className="mt-2 p-3 space-y-2 font-mono text-[11px]"
          style={{
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: '2px',
          }}
        >
          {checkRows.map((row) => {
            const st = CHECK_STATUS_STYLE[row.status] || CHECK_STATUS_STYLE.pass;
            return (
              <li key={row.id} className="flex justify-between gap-3 items-start">
                <span style={{ color: 'var(--text)' }}>
                  <span style={{ color: st.color, marginRight: '6px' }}>{st.icon}</span>
                  {row.label}
                </span>
                <span className="text-right text-muted shrink-0" style={{ maxWidth: '55%' }}>
                  {row.detail}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}


function ScenarioAdjustmentsBlock({ details }) {
  const adj = details?.scenario_adjustments;
  if (!adj || typeof adj !== 'object') return null;
  const parts = Object.entries(adj).map(([k, v]) => `${k}=${v}`);
  if (!parts.length) return null;
  return (
    <p className="font-mono mt-1.5 m-0" style={{ fontSize: '10px', color: 'var(--accent)', lineHeight: 1.45 }}>
      Adjustments: {parts.join(' · ')}
    </p>
  );
}

function LogisticsTraceBody({ step }) {
  const d = step.rawTrace?.details || step.details;
  if (!d?.is_retry_run) {
    return step.summary ? (
      <p className="font-mono mt-2 text-[11.5px] leading-relaxed" style={{ color: 'var(--muted)' }}>
        {step.summary}
      </p>
    ) : null;
  }

  const prev = d.previous_validator_failure;
  const attempt = d.attempt_number ?? (d.retry_count ?? 0) + 1;

  return (
    <div className="mt-3 space-y-2">
      <p className="font-mono m-0 font-bold" style={{ fontSize: '11px', color: '#9C27B0' }}>
        ↻ Re-solve attempt {attempt} after validation failure
      </p>
      {prev && (
        <p className="font-mono m-0 text-muted" style={{ fontSize: '10.5px', lineHeight: 1.5 }}>
          Prior failure: {formatViolationTypes(prev.reason_for_retry)}
          {prev.relaxation_factor_applied != null && (
            <span> · applying relaxation ×{prev.relaxation_factor_applied}</span>
          )}
        </p>
      )}
      {step.summary && (
        <p className="font-mono m-0 text-muted" style={{ fontSize: '10.5px' }}>
          {step.summary}
        </p>
      )}
      <ScenarioAdjustmentsBlock details={d} />
      <ToolChips toolCalls={step.tool_calls} />
    </div>
  );
}

function TraceStep({ step, isLast }) {
  const [open, setOpen] = useState(false);
  const color = colorForAgent(step.agent);
  const cleanName = step.agent.replace(/_agent$/, '').replace(/_/g, ' ');
  const isValidator = isValidatorAgent(step.agent);
  const isWeather = isWeatherAgent(step.agent);
  const isLogistics = isLogisticsAgent(step.agent);

  return (
    <li className="relative pb-4">
      {!isLast && (
        <span
          className="absolute left-[6px] top-7"
          style={{ bottom: '0', width: '1px', background: 'var(--border)' }}
        />
      )}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left flex gap-3"
      >
        <span
          className="mt-1.5 shrink-0"
          style={{
            display: 'inline-block',
            width: 12,
            height: 12,
            background: color,
            borderRadius: '2px',
          }}
        />
        <div
          className="flex-1 p-3"
          style={{
            background: 'rgba(255, 248, 231, 0.02)',
            borderLeft: `3px solid ${color}`,
            borderRadius: '2px',
          }}
        >
          <div className="flex justify-between items-baseline gap-3 flex-wrap">
            <span
              className="font-syne font-bold uppercase tracking-wider"
              style={{ color: 'var(--text)', fontSize: '13px' }}
            >
              {cleanName}
            </span>
            <span className="font-mono text-muted" style={{ fontSize: '0.75rem' }}>
              {step.duration_ms != null ? formatDuration(step.duration_ms) : '—'}
              {' · '}
              {formatExecutionLabel(step)}
            </span>
          </div>

          {isValidator ? (
            <ValidatorTraceBody step={step} />
          ) : isLogistics ? (
            <LogisticsTraceBody step={step} />
          ) : isWeather ? (
            <WeatherTraceBody step={step} />
          ) : (
            <>
              {step.summary && (
                <p
                  className="font-mono mt-2 text-[11.5px] leading-relaxed"
                  style={{ color: 'var(--muted)' }}
                >
                  {step.summary}
                </p>
              )}
              <ScenarioAdjustmentsBlock details={step.details} />
              <ToolChips toolCalls={step.tool_calls} />
            </>
          )}

          {open && !isValidator && !isWeather && !isLogistics && step.tool_calls?.length > 0 && (
            <div
              className="mt-3 p-2 font-mono text-[11px]"
              style={{
                background: 'var(--bg)',
                border: '1px solid var(--border)',
                borderRadius: '2px',
              }}
            >
              <p
                className="uppercase tracking-wider mb-1"
                style={{ color: 'var(--accent)', fontSize: '10px' }}
              >
                ▸ Tool detail
              </p>
              {step.tool_calls.map((tc, i) => (
                <div key={i} className="flex justify-between text-muted">
                  <span style={{ color: 'var(--text)' }}>
                    {tc.tool || tc.name || String(tc)}
                  </span>
                  <span>
                    {tc.duration_ms != null ? formatDuration(tc.duration_ms) : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </button>
    </li>
  );
}
