import { formatKg, formatCurrency } from '@/utils/formatters';

/**
 * RouteList — tabular summary of truck-by-truck assignments for a plan.
 */
export default function RouteList({ routes = [] }) {
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
          ▸ Route Assignments
        </h3>
        <span className="font-mono text-muted text-[11px] tracking-wider">
          {routes.length} TRUCKS
        </span>
      </div>
      {routes.length === 0 ? (
        <p className="px-5 py-6 font-mono text-muted text-[12px]">
          No routes in this plan yet.
        </p>
      ) : (
        <ul>
          {routes.map((r, idx) => (
            <li
              key={r.truckId || idx}
              className="px-5 py-3 flex justify-between"
              style={{ borderTop: idx === 0 ? 'none' : '1px solid var(--border)' }}
            >
              <div>
                <p
                  className="font-syne font-bold text-paper"
                  style={{ fontSize: '13px', letterSpacing: '0.05em' }}
                >
                  Truck {r.truckId || `#${idx + 1}`}
                </p>
                <p className="font-mono text-muted text-[11px] mt-1">
                  {r.stops?.length || 0} stops · {r.distance_km || '--'} km
                </p>
              </div>
              <div className="text-right">
                <p
                  className="font-syne font-bold"
                  style={{ color: 'var(--accent)', fontSize: '14px' }}
                >
                  {formatKg(r.loadKg)}
                </p>
                <p className="font-mono text-muted text-[11px] mt-1">
                  {formatCurrency(r.cost)}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
