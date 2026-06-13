import { etaFromMinutes, minutesUntilETA } from '@/utils/eta';

/**
 * TruckETACard — shows the assigned truck and its estimated arrival time.
 *
 * Props:
 *   farmId      string
 *   rawRoutes   Route[] from plan.route_plan.routes
 */
export default function TruckETACard({ farmId, rawRoutes = [] }) {
  let assignedTruck = null;
  let etaMinutes = null;

  for (const route of rawRoutes) {
    const stop = (route.stops || []).find(
      (s) => !s.demand_point_id && s.label === farmId,
    );
    if (stop) {
      assignedTruck = route.truck_id;
      etaMinutes = stop.eta_minutes_from_start ?? null;
      break;
    }
  }

  const etaTime = etaFromMinutes(etaMinutes);
  const minsLeft = minutesUntilETA(etaMinutes);

  if (!assignedTruck) {
    return (
      <div
        className="p-5"
        style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
      >
        <p className="font-mono uppercase text-[10px] tracking-widest mb-2" style={{ color: 'var(--muted)' }}>
          Truck ETA
        </p>
        <p className="font-mono text-[12px]" style={{ color: 'var(--muted)' }}>
          No truck assigned for this run yet.
        </p>
      </div>
    );
  }

  const isLate = minsLeft != null && minsLeft < 0;
  const isSoon = minsLeft != null && minsLeft >= 0 && minsLeft < 30;
  const countdownColor = isLate ? 'var(--red-risk)' : isSoon ? 'var(--accent)' : 'var(--green-ok)';

  return (
    <div
      className="p-5"
      style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
    >
      <p className="font-mono uppercase text-[10px] tracking-widest mb-3" style={{ color: 'var(--muted)' }}>
        Assigned Truck
      </p>

      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-syne font-bold text-paper" style={{ fontSize: '18px' }}>
            {assignedTruck}
          </p>
          {etaTime && (
            <p className="font-mono mt-1 text-[12px]" style={{ color: 'var(--muted)' }}>
              Estimated arrival: <span style={{ color: 'var(--text)' }}>{etaTime}</span>
            </p>
          )}
        </div>

        {minsLeft != null && (
          <div className="text-right">
            <p className="font-syne font-bold" style={{ fontSize: '22px', color: countdownColor }}>
              {isLate ? `${Math.abs(minsLeft)}m late` : `${minsLeft}m`}
            </p>
            <p className="font-mono text-[10px] uppercase tracking-wider" style={{ color: 'var(--muted)' }}>
              {isLate ? 'overdue' : 'until arrival'}
            </p>
          </div>
        )}
      </div>

      <div
        className="mt-4 pt-4 flex items-center gap-2"
        style={{ borderTop: '1px solid var(--border)' }}
      >
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: isSoon || isLate ? 'var(--accent)' : 'var(--green-ok)', flexShrink: 0 }}
        />
        <p className="font-mono text-[11px]" style={{ color: 'var(--muted)' }}>
          {isLate
            ? 'Truck has passed estimated arrival — check transport team.'
            : isSoon
            ? 'Truck arriving soon — have crop ready at collection point.'
            : 'Truck en route. Prepare harvest for pickup.'}
        </p>
      </div>
    </div>
  );
}
