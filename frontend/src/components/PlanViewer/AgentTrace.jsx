import { useState } from 'react';
import { formatDuration } from '@/utils/formatters';

/**
 * AgentTrace — vertical timeline of per-agent reasoning steps.
 * Each card is collapsible and shows duration, tool calls, and token usage.
 */
export default function AgentTrace({ traces }) {
  // TODO: replace mock with real trace payload from GET /api/run/:id/traces.
  const mock = [
    {
      agent: 'orchestrator',
      duration_ms: 120,
      token_count: 0,
      tool_calls: [{ tool: 'input_validation', duration_ms: 40 }],
      summary: 'Validated inputs, loaded past outcomes from store.',
    },
    {
      agent: 'weather_agent',
      duration_ms: 1840,
      token_count: 420,
      tool_calls: [
        { tool: 'openweather.forecast', duration_ms: 950 },
        { tool: 'redis.cache.set', duration_ms: 20 },
      ],
      summary: '5 farms flagged SEVERE, 3 WARNING, 12 NORMAL.',
    },
    {
      agent: 'demand_agent',
      duration_ms: 1720,
      token_count: 510,
      tool_calls: [{ tool: 'outcome_store.query', duration_ms: 210 }],
      summary: 'Demand forecast adjusted -18% for Mandi A on Tuesday.',
    },
    {
      agent: 'inventory_agent',
      duration_ms: 610,
      token_count: 280,
      tool_calls: [],
      summary: '3,400 kg at risk of spoilage within 48h.',
    },
    {
      agent: 'logistics_agent',
      duration_ms: 12_400,
      token_count: 150,
      tool_calls: [{ tool: 'ortools.vrp_solve', duration_ms: 11_900 }],
      summary: 'VRP solved in 11.9s with 10 trucks, 42 stops.',
    },
    {
      agent: 'validator',
      duration_ms: 85,
      token_count: 0,
      tool_calls: [{ tool: 'constraint_checker', duration_ms: 60 }],
      summary: 'All time windows and capacities satisfied.',
    },
  ];

  const list = traces?.agent_steps || mock;

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="px-5 py-3 border-b border-gray-200">
        <h3 className="font-semibold text-agri-green-dark">Agent Reasoning Trace</h3>
        <p className="text-xs text-gray-500">{list.length} agent steps</p>
      </div>
      <ol className="relative">
        {list.map((step, idx) => (
          <TraceStep key={idx} step={step} isLast={idx === list.length - 1} />
        ))}
      </ol>
    </div>
  );
}

/** Collapsible single-step card inside the agent trace timeline. */
function TraceStep({ step, isLast }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="relative pl-10 pr-5 py-4">
      <span className="absolute left-4 top-5 w-3 h-3 rounded-full bg-agri-green" />
      {!isLast && (
        <span className="absolute left-[21px] top-8 bottom-0 w-px bg-gray-200" />
      )}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left"
      >
        <div className="flex justify-between items-baseline">
          <span className="font-medium text-sm">{step.agent}</span>
          <span className="text-xs text-gray-500">
            {formatDuration(step.duration_ms)} • {step.token_count ?? 0} tokens
          </span>
        </div>
        <p className="text-xs text-gray-600 mt-1">{step.summary}</p>
      </button>
      {open && (
        <div className="mt-3 bg-gray-50 rounded-md p-3 text-xs space-y-1">
          <p className="font-semibold text-gray-700">Tool calls</p>
          {step.tool_calls?.length ? (
            step.tool_calls.map((tc, i) => (
              <div key={i} className="flex justify-between">
                <span>{tc.tool}</span>
                <span className="text-gray-500">{formatDuration(tc.duration_ms)}</span>
              </div>
            ))
          ) : (
            <p className="text-gray-500 italic">No tool calls</p>
          )}
        </div>
      )}
    </li>
  );
}
