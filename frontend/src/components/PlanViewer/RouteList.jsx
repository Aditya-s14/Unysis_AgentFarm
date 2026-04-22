import { formatKg, formatCurrency } from '@/utils/formatters';

/**
 * RouteList — tabular summary of truck-by-truck assignments for a plan.
 */
export default function RouteList({ routes = [] }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="px-5 py-3 border-b border-gray-200">
        <h3 className="font-semibold text-agri-green-dark">Route Assignments</h3>
        <p className="text-xs text-gray-500">{routes.length} trucks dispatched</p>
      </div>
      {routes.length === 0 ? (
        <p className="p-5 text-sm text-gray-500 italic">No routes in this plan yet.</p>
      ) : (
        <ul className="divide-y divide-gray-100">
          {routes.map((r, idx) => (
            <li key={r.truckId || idx} className="px-5 py-3 flex justify-between text-sm">
              <div>
                <p className="font-medium">Truck {r.truckId || `#${idx + 1}`}</p>
                <p className="text-xs text-gray-500">
                  {r.stops?.length || 0} stops • {r.distance_km || '--'} km
                </p>
              </div>
              <div className="text-right">
                <p>{formatKg(r.loadKg)}</p>
                <p className="text-xs text-gray-500">{formatCurrency(r.cost)}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
