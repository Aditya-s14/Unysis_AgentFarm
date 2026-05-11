import { useState } from 'react';
import { formatDuration } from '@/utils/formatters';

/**
 * AgentTrace — vertical timeline of per-agent reasoning steps.
 * Each card is collapsible and shows duration, tool calls, and token usage.
 *
 * Backend trace shape (per item):
 *   { agent_name, start_time, end_time, tools_used, notes, token_count }
 *
 * `traces` may also be the wrapper shape `{ agent_steps: [...] }` for
 * backwards compatibility.
 */
const AGENT_COLOR = {
  orchestrator: 'var(--accent)',
  weather:      '#2196F3',
  demand:       '#FF9800',
  inventory:    'var(--green-ok)',
  logistics:    '#9C27B0',
  validator:    'var(--muted)',
};

function colorForAgent(name) {
  const key = (name || '').toLowerCase().replace(/_agent$/, '');
  return AGENT_COLOR[key] || 'var(--accent)';
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
            <TraceStep
              key={idx}
              step={step}
              isLast={idx === list.length - 1}
            />
          ))}
        </ol>
      )}
    </div>
  );
}

function normaliseStep(t) {
  if (!t) {
    return { agent: 'unknown', duration_ms: null, summary: '', tool_calls: [], token_count: 0 };
  }
  const agent = t.agent || t.agent_name || 'unknown';
  const summary = t.summary || t.notes || '';
  const tokenCount = t.token_count ?? t.tokenCount ?? 0;

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

  return { agent, duration_ms: duration, token_count: tokenCount, summary, tool_calls: toolCalls };
}

function TraceStep({ step, isLast }) {
  const [open, setOpen] = useState(false);
  const color = colorForAgent(step.agent);
  const cleanName = step.agent.replace(/_agent$/, '').replace(/_/g, ' ');

  return (
    <li className="relative pb-4">
      {!isLast && (
        <span
          className="absolute left-[6px] top-7"
          style={{
            bottom: '0',
            width: '1px',
            background: 'var(--border)',
          }}
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
            <span
              className="font-mono text-muted"
              style={{ fontSize: '0.75rem' }}
            >
              {step.duration_ms != null ? formatDuration(step.duration_ms) : '—'}
              {' · '}
              {step.token_count ?? 0} tok
            </span>
          </div>
          {step.summary && (
            <p
              className="font-mono mt-2 text-[11.5px] leading-relaxed"
              style={{ color: 'var(--muted)' }}
            >
              {step.summary}
            </p>
          )}
          {open && (
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
                ▸ Tool Calls
              </p>
              {step.tool_calls?.length ? (
                step.tool_calls.map((tc, i) => (
                  <div key={i} className="flex justify-between text-muted">
                    <span style={{ color: 'var(--text)' }}>
                      {tc.tool || tc.name || String(tc)}
                    </span>
                    <span>
                      {tc.duration_ms != null ? formatDuration(tc.duration_ms) : ''}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-muted italic">No tool calls</p>
              )}
            </div>
          )}
        </div>
      </button>
    </li>
  );
}
