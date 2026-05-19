import { useEffect, useMemo, useState } from 'react';
import {
  buildSimulationSteps,
  formatViolationTypes,
  hasRetryLoop,
  validatorRetryCounterLabel,
} from '@/utils/retryLoopTrace';
const AGENT_LABELS = {
  orchestrator_entry: 'Orchestrator (init) — validating inputs',
  weather_agent: 'Weather Agent — fetching forecasts',
  demand_agent: 'Demand Agent — forecasting mandis',
  inventory_agent: 'Inventory Agent — calculating spoilage',
  logistics_agent: 'Logistics Agent — solving routes (OR-Tools)',
  validator: 'Validator — checking plan feasibility',
  orchestrator_exit: 'Orchestrator (finalise) — packaging final plan',
};

const AGENT_COLORS = {
  orchestrator_entry: '#F5A623',
  weather_agent: '#2196F3',
  demand_agent: '#FF9800',
  inventory_agent: '#4CAF50',
  logistics_agent: '#9C27B0',
  validator: '#8A9E8C',
  orchestrator_exit: '#F5A623',
  retry_banner: '#E53935',
};

const PIPELINE_COMPLETE_MSG =
  'Pipeline completed — 6 agents (Weather, Demand, Inventory, Logistics, Validator, Orchestrator)';

const LOGICAL_AGENT_COUNT = 6;

function labelForStep(step) {
  if (step.kind === 'retry_banner') {
    const factor = step.relaxation != null ? ` ×${step.relaxation}` : '';
    return `Retry prep — relaxing constraints${factor}`;
  }
  if (step.key === 'logistics_agent' && step.isRetry) {
    return `Logistics Agent — re-solving routes (attempt ${step.attempt})`;
  }
  if (step.key === 'validator' && step.details) {
    const n = validatorRetryCounterLabel(step.details);
    if (step.details.retry_triggered) {
      return `Validator — failed (${n || 'retry'})`;
    }
    if (step.details.max_retries_reached) {
      return 'Validator — max retries reached';
    }
  }
  return AGENT_LABELS[step.key] || step.key;
}

function colorForStep(step) {
  if (step.kind === 'retry_banner') return AGENT_COLORS.retry_banner;
  return AGENT_COLORS[step.key] || 'var(--accent)';
}

function splitSteps(steps) {
  const firstLogistics = steps.findIndex((s) => s.key === 'logistics_agent');
  const exitIdx = steps.findIndex((s) => s.key === 'orchestrator_exit');
  if (firstLogistics < 0) {
    return { prefix: steps, loop: [], suffix: [] };
  }
  const prefix = steps.slice(0, firstLogistics);
  const loopEnd = exitIdx >= 0 ? exitIdx : steps.length;
  const loop = steps.slice(firstLogistics, loopEnd);
  const suffix = exitIdx >= 0 ? steps.slice(exitIdx) : [];
  return { prefix, loop, suffix };
}

function PipelineConnector() {
  return (
    <div
      className="font-mono text-muted flex justify-center py-0.5"
      style={{ fontSize: '14px', letterSpacing: '0.05em', opacity: 0.55 }}
      aria-hidden
    >
      ↓
    </div>
  );
}

function SectionLabel({ icon, title, subtitle }) {
  return (
    <div
      className="flex items-baseline gap-2 px-1 pt-1 pb-2"
      style={{ borderBottom: '1px solid var(--border)' }}
    >
      <span style={{ fontSize: '13px', lineHeight: 1 }}>{icon}</span>
      <div>
        <p
          className="font-mono uppercase"
          style={{ fontSize: '9px', letterSpacing: '0.16em', color: 'var(--accent)' }}
        >
          {title}
        </p>
        {subtitle && (
          <p className="font-mono text-muted" style={{ fontSize: '10px', marginTop: '2px' }}>
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * SimulationPanel — animates pipeline steps; expands when validator retries occur.
 */
export default function SimulationPanel({
  traces = [],
  isRunning = false,
  scenarioType = 'monsoon_disruption',
  onComplete,
}) {
  const steps = useMemo(() => buildSimulationSteps(traces), [traces]);
  const { prefix, loop, suffix } = useMemo(() => splitSteps(steps), [steps]);
  const showRetry = hasRetryLoop(traces);
  const [animStep, setAnimStep] = useState(-1);

  useEffect(() => {
    if (!steps.length) return;
    setAnimStep(0);
  }, [steps]);

  useEffect(() => {
    if (animStep < 0 || animStep >= steps.length) {
      if (animStep >= steps.length) onComplete?.();
      return;
    }
    const delay = steps[animStep]?.kind === 'retry_banner' ? 900 : 600;
    const t = setTimeout(() => setAnimStep((s) => s + 1), delay);
    return () => clearTimeout(t);
  }, [animStep, steps, onComplete]);

  const stepsRemaining = animStep < 0 ? steps.length : Math.max(0, steps.length - animStep);
  const allDone = animStep >= steps.length;

  const headerSubline = allDone
    ? showRetry
      ? 'Adaptive retry loop completed — validator re-ran with relaxed constraints'
      : '5 core agents + orchestrator · all steps complete'
    : animStep < 0
      ? 'Pipeline: 6 agents executing (5 core + orchestrator)'
      : `${stepsRemaining} pipeline step${stepsRemaining === 1 ? '' : 's'} remaining`;

  const renderStep = (step, globalIndex) => {
    const state = animStep > globalIndex ? 'DONE' : animStep === globalIndex ? 'RUNNING' : 'PENDING';
    if (step.kind === 'retry_banner') {
      return (
        <RetryBannerRow
          key={step.id}
          state={state}
          retryCount={step.retryCount}
          relaxation={step.relaxation}
          demandScale={step.demandScale}
          reasons={step.reasons}
        />
      );
    }
    const trace = step.trace;
    let durationMs = null;
    if (trace?.start_time && trace?.end_time) {
      const s = Date.parse(trace.start_time);
      const e = Date.parse(trace.end_time);
      if (!Number.isNaN(s) && !Number.isNaN(e)) durationMs = Math.max(0, e - s);
    }
    const extraNotes = step.key === 'validator' && step.details?.retry_triggered
      ? 'Validation failed — routing again with relaxed constraints'
      : step.key === 'validator' && step.details?.max_retries_reached
        ? 'Plan requires human review'
        : '';

    return (
      <AgentRow
        key={step.id}
        color={colorForStep(step)}
        label={labelForStep(step)}
        state={state}
        notes={extraNotes || trace?.notes || ''}
        tokenCount={trace?.token_count ?? null}
        durationMs={durationMs}
        highlight={step.key === 'validator' && step.details?.retry_triggered}
        failHighlight={step.key === 'validator' && step.details?.max_retries_reached}
      />
    );
  };

  let globalIdx = 0;

  return (
    <div
      className="bg-card"
      style={{ border: '1px solid var(--border)', borderRadius: '4px', overflow: 'hidden' }}
    >
      <div
        className="px-5 py-4 flex items-center gap-3"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <span className="font-mono text-accent" style={{ fontSize: '11px', letterSpacing: '0.12em' }}>AI</span>
        <div className="flex-1 min-w-0">
          <h2
            className="font-syne font-bold uppercase tracking-wider-2"
            style={{ fontSize: '14px', color: 'var(--accent)' }}
          >
            {scenarioType.replace(/_/g, ' ').toUpperCase()} — PIPELINE
          </h2>
          <p className="font-mono mt-1" style={{ fontSize: '11px', color: 'var(--muted)' }}>
            {headerSubline}
          </p>
        </div>
        <span
          className="font-mono uppercase shrink-0 hidden sm:inline"
          style={{
            fontSize: '9px',
            letterSpacing: '0.12em',
            color: 'var(--accent)',
            border: '1px solid rgba(245, 166, 35, 0.4)',
            borderRadius: '2px',
            padding: '4px 8px',
          }}
        >
          {LOGICAL_AGENT_COUNT} agents
        </span>
      </div>

      {allDone && showRetry && (
        <div
          className="px-5 py-3 font-mono"
          style={{
            fontSize: '11.5px',
            lineHeight: 1.55,
            color: 'var(--red-risk)',
            background: 'rgba(229, 57, 53, 0.06)',
            borderBottom: '1px solid var(--border)',
          }}
        >
          Validator retry loop observed — constraints were relaxed and logistics re-ran.
        </div>
      )}

      {allDone && !showRetry && (
        <div
          className="px-5 py-3 font-mono"
          style={{
            fontSize: '11.5px',
            lineHeight: 1.55,
            color: 'var(--green-ok)',
            background: 'rgba(76, 175, 80, 0.08)',
            borderBottom: '1px solid var(--border)',
          }}
        >
          OK — {PIPELINE_COMPLETE_MSG}
        </div>
      )}

      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <SectionLabel icon="*" title="Orchestrator" subtitle="control layer · init" />
        <OrchestratorGroup>
          {prefix
            .filter((s) => s.key === 'orchestrator_entry')
            .map((step) => {
              const el = renderStep(step, globalIdx);
              globalIdx += 1;
              return el;
            })}
        </OrchestratorGroup>

        <PipelineConnector />

        <SectionLabel
          icon=">"
          title="Core pipeline"
          subtitle={
            showRetry
              ? 'weather → demand → inventory → logistics ↔ validator (adaptive retry)'
              : '5 agents — weather → demand → inventory → logistics → validator'
          }
        />
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {prefix
            .filter((s) => s.key !== 'orchestrator_entry')
            .map((step) => {
              const el = renderStep(step, globalIdx);
              globalIdx += 1;
              return el;
            })}
          {loop.length > 0 && (
            <div
              style={{
                border: showRetry ? '1px dashed rgba(229, 57, 53, 0.35)' : 'none',
                borderRadius: '4px',
                padding: showRetry ? '8px' : 0,
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              {showRetry && (
                <p
                  className="font-mono uppercase m-0 px-1"
                  style={{ fontSize: '9px', letterSpacing: '0.14em', color: 'var(--red-risk)' }}
                >
                  Routing & validation loop
                </p>
              )}
              {loop.map((step) => {
                const el = renderStep(step, globalIdx);
                globalIdx += 1;
                return el;
              })}
            </div>
          )}
        </div>

        {suffix.length > 0 && (
          <>
            <PipelineConnector />
            <SectionLabel icon="*" title="Orchestrator" subtitle="control layer · finalise" />
            <OrchestratorGroup>
              {suffix.map((step) => {
                const el = renderStep(step, globalIdx);
                globalIdx += 1;
                return el;
              })}
            </OrchestratorGroup>
          </>
        )}
      </div>
    </div>
  );
}

function OrchestratorGroup({ children }) {
  return (
    <div
      style={{
        border: '1px solid rgba(245, 166, 35, 0.25)',
        borderLeft: '3px solid var(--accent)',
        borderRadius: '4px',
        background: 'rgba(245, 166, 35, 0.04)',
        padding: '4px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
      }}
    >
      {children}
    </div>
  );
}

function RetryBannerRow({ state, retryCount, relaxation, demandScale, reasons }) {
  const isPending = state === 'PENDING';
  const isRunning = state === 'RUNNING';
  const isDone = state === 'DONE';
  const color = AGENT_COLORS.retry_banner;

  return (
    <div
      style={{
        borderLeft: `3px solid ${isPending ? 'var(--border)' : color}`,
        padding: '10px 14px',
        background: 'rgba(229, 57, 53, 0.05)',
        borderRadius: '0 2px 2px 0',
        opacity: isPending ? 0.5 : 1,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <StatusDot color={color} state={state} />
        <span className="font-syne font-bold uppercase" style={{ fontSize: '12px', color: 'var(--red-risk)' }}>
          Validation failed — retrying logistics
        </span>
        {retryCount != null && (
          <span className="font-mono text-muted" style={{ fontSize: '10px' }}>
            Retry {retryCount}/2
          </span>
        )}
      </div>
      {isRunning && (
        <p className="font-mono mt-2 m-0" style={{ fontSize: '11px', color }}>
          Applying relaxed constraints…
        </p>
      )}
      {isDone && (
        <p className="font-mono mt-2 m-0 text-muted" style={{ fontSize: '10.5px', lineHeight: 1.5 }}>
          {formatViolationTypes(reasons)}
          {relaxation != null && ` · relaxation ×${relaxation}`}
          {demandScale != null && ` · demand scale ${demandScale}`}
        </p>
      )}
    </div>
  );
}

function AgentRow({
  color,
  label,
  state,
  notes,
  tokenCount,
  durationMs,
  nested = false,
  highlight = false,
  failHighlight = false,
}) {
  const isPending = state === 'PENDING';
  const isRunning = state === 'RUNNING';
  const isDone = state === 'DONE';

  let borderColor = isPending ? 'var(--border)' : color;
  if (highlight) borderColor = 'var(--red-risk)';
  if (failHighlight) borderColor = '#FF9800';

  return (
    <div
      style={{
        borderLeft: nested ? 'none' : `3px solid ${borderColor}`,
        padding: nested ? '10px 12px' : '12px 16px',
        background: highlight
          ? 'rgba(229, 57, 53, 0.04)'
          : nested
            ? 'transparent'
            : 'var(--bg-card)',
        borderRadius: nested ? '2px' : '0 2px 2px 0',
        transition: 'all 0.3s ease',
        opacity: isPending ? 0.45 : 1,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
          <StatusDot color={color} state={state} />
          <span
            className="font-syne font-bold uppercase tracking-wider"
            style={{
              fontSize: nested ? '12px' : '13px',
              color: isPending ? 'var(--muted)' : 'var(--text)',
            }}
          >
            {label}
          </span>
        </div>

        <div
          className="font-mono"
          style={{
            fontSize: '11px',
            color: 'var(--muted)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            flexShrink: 0,
          }}
        >
          {isDone && durationMs != null && (
            <span>{durationMs < 1000 ? `${durationMs}ms` : `${(durationMs / 1000).toFixed(1)}s`}</span>
          )}
          {isDone && tokenCount != null && tokenCount > 0 && (
            <span>{tokenCount} tok</span>
          )}
          {isDone && <span style={{ color: failHighlight ? '#FF9800' : '#4CAF50', fontWeight: 700 }}>{failHighlight ? '!' : '✓'}</span>}
          {isRunning && <span style={{ color }}>●</span>}
          {isPending && <span style={{ opacity: 0.4 }}>○</span>}
        </div>
      </div>

      {isDone && notes && (
        <p className="font-mono mt-2 m-0" style={{ fontSize: '11.5px', color: 'var(--muted)', lineHeight: 1.55 }}>
          {notes.length > 140 ? `${notes.slice(0, 140)}…` : notes}
        </p>
      )}
      {isRunning && (
        <p className="font-mono mt-1 m-0" style={{ fontSize: '11px', color }}>
          running...
        </p>
      )}
      {isPending && (
        <p className="font-mono mt-1 m-0" style={{ fontSize: '11px', color: 'var(--muted)' }}>
          waiting...
        </p>
      )}
    </div>
  );
}

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
  if (state === 'RUNNING') {
    return (
      <span
        style={{ ...base, background: color, animation: 'agent-pulse 1s ease-in-out infinite' }}
      />
    );
  }
  return <span style={{ ...base, background: color }} />;
}
