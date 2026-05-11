import { useEffect, useState } from 'react';

const AGENT_ORDER = [
  'orchestrator_entry',
  'weather_agent',
  'demand_agent',
  'inventory_agent',
  'logistics_agent',
  'validator',
  'orchestrator_exit',
];

const AGENT_LABELS = {
  orchestrator_entry: 'Orchestrator — validating inputs',
  weather_agent:      'Weather Agent — fetching forecasts',
  demand_agent:       'Demand Agent — forecasting mandis',
  inventory_agent:    'Inventory Agent — calculating spoilage',
  logistics_agent:    'Logistics Agent — solving routes (OR-Tools)',
  validator:          'Validator — checking plan feasibility',
  orchestrator_exit:  'Orchestrator — packaging final plan',
};

const AGENT_COLORS = {
  orchestrator_entry: '#F5A623',
  weather_agent:      '#2196F3',
  demand_agent:       '#FF9800',
  inventory_agent:    '#4CAF50',
  logistics_agent:    '#9C27B0',
  validator:          '#8A9E8C',
  orchestrator_exit:  '#F5A623',
};

/**
 * SimulationPanel — animates agent execution rows as the pipeline runs.
 *
 * Props:
 *   traces    AgentTrace[]  Final traces from the backend.  Pass [] while API is pending.
 *   isRunning bool          True while the API call is in flight or the animation is playing.
 *   onComplete fn           Called once the last agent row transitions to DONE.
 */
export default function SimulationPanel({ traces = [], isRunning = false, onComplete }) {
  // -1 = not started, 0..6 = agent currently animating, 7 = all done
  const [animStep, setAnimStep] = useState(-1);

  // Kick off animation when traces arrive
  useEffect(() => {
    if (!traces || traces.length === 0) return;
    setAnimStep(0);
  }, [traces]);

  // Advance one step every 600 ms
  useEffect(() => {
    if (animStep < 0 || animStep >= AGENT_ORDER.length) {
      if (animStep >= AGENT_ORDER.length) onComplete?.();
      return;
    }
    const t = setTimeout(() => setAnimStep((s) => s + 1), 600);
    return () => clearTimeout(t);
  }, [animStep, onComplete]);

  // Build agent_name → trace lookup
  const traceByAgent = {};
  (traces || []).forEach((tr) => {
    const k = tr.agent_name || tr.agent || '';
    if (k) traceByAgent[k] = tr;
  });

  const remaining = animStep < 0 ? AGENT_ORDER.length : Math.max(0, AGENT_ORDER.length - animStep);
  const allDone   = animStep >= AGENT_ORDER.length;

  return (
    <div
      className="bg-card"
      style={{ border: '1px solid var(--border)', borderRadius: '4px', overflow: 'hidden' }}
    >
      {/* ── Header ── */}
      <div
        className="px-5 py-4 flex items-center gap-3"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <span style={{ fontSize: '22px', lineHeight: 1 }}>🤖</span>
        <div>
          <h2
            className="font-syne font-bold uppercase tracking-wider-2"
            style={{ fontSize: '14px', color: 'var(--accent)' }}
          >
            AGENTS RUNNING — MONSOON DISRUPTION
          </h2>
          <p className="font-mono mt-1" style={{ fontSize: '11px', color: 'var(--muted)' }}>
            {allDone
              ? 'all agents complete ✓'
              : animStep < 0
              ? '7 autonomous agents optimising supply chain...'
              : `${remaining} agent${remaining === 1 ? '' : 's'} remaining...`}
          </p>
        </div>
      </div>

      {/* ── Agent rows ── */}
      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {AGENT_ORDER.map((key, idx) => {
          const rowState =
            animStep > idx ? 'DONE' : animStep === idx ? 'RUNNING' : 'PENDING';
          const trace   = traceByAgent[key];
          const color   = AGENT_COLORS[key];
          const label   = AGENT_LABELS[key];

          let durationMs = null;
          if (trace?.start_time && trace?.end_time) {
            const s = Date.parse(trace.start_time);
            const e = Date.parse(trace.end_time);
            if (!isNaN(s) && !isNaN(e)) durationMs = Math.max(0, e - s);
          }

          return (
            <AgentRow
              key={key}
              color={color}
              label={label}
              state={rowState}
              notes={trace?.notes || ''}
              tokenCount={trace?.token_count ?? null}
              durationMs={durationMs}
            />
          );
        })}
      </div>
    </div>
  );
}

/* ── Single agent row ─────────────────────────────────────────────────────── */
function AgentRow({ color, label, state, notes, tokenCount, durationMs }) {
  const isPending = state === 'PENDING';
  const isRunning = state === 'RUNNING';
  const isDone    = state === 'DONE';

  return (
    <div
      style={{
        borderLeft: `3px solid ${isPending ? 'var(--border)' : color}`,
        padding: '12px 16px',
        background: 'var(--bg-card)',
        borderRadius: '0 2px 2px 0',
        transition: 'all 0.3s ease',
        opacity: isPending ? 0.45 : 1,
      }}
    >
      {/* Row header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <StatusDot color={color} state={state} />
          <span
            className="font-syne font-bold uppercase tracking-wider"
            style={{
              fontSize: '13px',
              color: isPending ? 'var(--muted)' : 'var(--text)',
            }}
          >
            {label}
          </span>
        </div>

        {/* Right-side metadata */}
        <div
          className="font-mono"
          style={{ fontSize: '11px', color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}
        >
          {isDone && durationMs != null && (
            <span>{durationMs < 1000 ? `${durationMs}ms` : `${(durationMs / 1000).toFixed(1)}s`}</span>
          )}
          {isDone && tokenCount != null && tokenCount > 0 && (
            <span>{tokenCount} tok</span>
          )}
          {isDone    && <span style={{ color: '#4CAF50', fontWeight: 700 }}>✓</span>}
          {isRunning && <span style={{ color }}>●</span>}
          {isPending && <span style={{ opacity: 0.4 }}>○</span>}
        </div>
      </div>

      {/* Sub-text */}
      {isDone && notes && (
        <p
          className="font-mono mt-2"
          style={{ fontSize: '11.5px', color: 'var(--muted)', lineHeight: 1.55 }}
        >
          {notes.length > 110 ? notes.slice(0, 110) + '…' : notes}
        </p>
      )}
      {isRunning && (
        <p className="font-mono mt-1" style={{ fontSize: '11px', color }}>
          running...
        </p>
      )}
      {isPending && (
        <p className="font-mono mt-1" style={{ fontSize: '11px', color: 'var(--muted)' }}>
          waiting...
        </p>
      )}
    </div>
  );
}

/* ── Status dot (pure CSS animation handled by globals.css keyframe) ───────── */
function StatusDot({ color, state }) {
  const base = {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    flexShrink: 0,
    display: 'inline-block',
    transition: 'background 0.3s ease',
  };
  if (state === 'PENDING') return <span style={{ ...base, background: 'var(--border)' }} />;
  if (state === 'RUNNING')
    return <span style={{ ...base, background: color, animation: 'agent-pulse 1s ease-in-out infinite' }} />;
  return <span style={{ ...base, background: color }} />;
}
