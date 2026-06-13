import RouteList from './RouteList';
import KPIGrid from '@/components/KPICards/KPIGrid';

/**
 * PlanViewer — top-level view of a single run.
 * Combines KPI summary and route list.
 */
export default function PlanViewer({ run }) {
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
      <RouteList routes={run.plan?.assignments || []} />
    </div>
  );
}
