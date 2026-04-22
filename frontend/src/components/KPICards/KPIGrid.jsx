import KPICard from './KPICard';
import { formatCurrency, formatPercentage } from '@/utils/formatters';

/**
 * KPIGrid — renders the four headline KPIs for a given run.
 * Accepts a `kpis` prop; when missing, renders a mock TODO set for the skeleton UI.
 */
export default function KPIGrid({ kpis }) {
  // TODO: replace mock defaults once backend returns KPI payload.
  const effective = kpis || {
    wasteReductionPct: 0.27,
    onTimeDeliveryPct: 0.91,
    totalCost: 184_500,
    replanCount: 2,
    baselineOnTimePct: 0.78,
    costDelta: -0.12,
    replanDelta: 0,
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <KPICard
        title="Waste Reduction"
        value={formatPercentage(effective.wasteReductionPct)}
        delta={effective.wasteReductionPct}
        improvementDirection="up"
        subtitle="vs naive baseline"
      />
      <KPICard
        title="On-Time Delivery"
        value={formatPercentage(effective.onTimeDeliveryPct)}
        delta={effective.onTimeDeliveryPct - (effective.baselineOnTimePct ?? 0.75)}
        improvementDirection="up"
        subtitle="vs naive baseline"
      />
      <KPICard
        title="Total Cost"
        value={formatCurrency(effective.totalCost)}
        delta={effective.costDelta}
        improvementDirection="down"
        subtitle="fuel + handling"
      />
      <KPICard
        title="Re-plan Count"
        value={String(effective.replanCount)}
        delta={effective.replanDelta}
        improvementDirection="down"
        subtitle="validator retries"
      />
    </div>
  );
}
