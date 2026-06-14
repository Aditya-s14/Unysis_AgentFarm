import KPICard from './KPICard';
import { formatKg, formatPercentage } from '@/utils/formatters';

/**
 * KPIGrid — renders the four headline KPIs for a given run.
 *
 * Accepts the raw `kpis` object the backend returns from
 * POST /api/scenario/run.  Recognised fields:
 *
 *   waste_reduction_pct     0-100 percentage (vs naive demand-matching baseline)
 *   naive_waste_kg          kg wasted under the naive baseline
 *   optimized_waste_kg      kg wasted under the VRP-optimised plan
 *   naive_waste_pct         0-100, naive waste as % of total at-risk produce
 *   optimized_waste_pct     0-100, optimised waste as % of total at-risk
 *   route_count             number of trucks dispatched
 *   retry_count             number of validator retries
 *   coverage_pct            0-100, % of at-risk farms covered by a route
 *
 * When `kpis` is null/undefined the cards render `--` placeholders.
 */
export default function KPIGrid({ kpis }) {
  const k = kpis || {};

  const wastePct = Number(k.waste_reduction_pct);
  const naiveKg = Number(k.naive_waste_kg);
  const optimizedKg = Number(k.optimized_waste_kg);
  const naiveWastePct = Number(k.naive_waste_pct);
  const optimizedWastePct = Number(k.optimized_waste_pct);
  const coveragePct = Number(k.coverage_pct);
  const routeCount = Number(k.route_count);
  const retryCount = Number(k.retry_count);

  // Convert backend's 0-100 to the fraction the KPICard delta badge expects.
  const wasteReductionFraction = Number.isFinite(wastePct) ? wastePct / 100 : undefined;
  const coverageFraction = Number.isFinite(coveragePct) ? coveragePct / 100 : undefined;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <KPICard
        title="Waste Reduction"
        value={formatPercentage(wasteReductionFraction)}
        delta={wasteReductionFraction}
        improvementDirection="up"
        subtitle="vs naive baseline"
      />
      <KPICard
        title="Naive Waste"
        value={Number.isFinite(naiveKg) ? formatKg(naiveKg) : '--'}
        delta={undefined}
        improvementDirection="down"
        subtitle={
          Number.isFinite(naiveWastePct)
            ? `${naiveWastePct.toFixed(1)}% of at-risk produce`
            : 'what would spoil without VRP'
        }
      />
      <KPICard
        title="Optimised Waste"
        value={Number.isFinite(optimizedKg) ? formatKg(optimizedKg) : '--'}
        delta={undefined}
        improvementDirection="down"
        subtitle={
          Number.isFinite(optimizedWastePct)
            ? `${optimizedWastePct.toFixed(1)}% of at-risk produce`
            : 'optimised plan'
        }
      />
      <KPICard
        title="Routes Dispatched"
        value={Number.isFinite(routeCount) ? String(Math.round(routeCount)) : '--'}
        delta={undefined}
        improvementDirection="down"
        subtitle={
          Number.isFinite(retryCount)
            ? `${Math.round(retryCount)} validator retries · ${
                Number.isFinite(coverageFraction)
                  ? formatPercentage(coverageFraction)
                  : '--'
              } coverage`
            : 'trucks in plan'
        }
      />
    </div>
  );
}
