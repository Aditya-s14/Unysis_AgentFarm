import RouteList from './RouteList';
import AgentTrace from './AgentTrace';
import KPIGrid from '@/components/KPICards/KPIGrid';

/**
 * PlanViewer — top-level view of a single run.
 * Combines KPI summary, route list, and the agent reasoning trace.
 */
export default function PlanViewer({ run, traces }) {
  if (!run) {
    return (
      <div className="font-mono text-muted text-[13px] italic">
        No plan loaded. Run a scenario or select a run from the Runs page.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <KPIGrid kpis={run.kpis} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RouteList routes={run.plan?.assignments || []} />
        <AgentTrace traces={traces} />
      </div>
    </div>
  );
}
