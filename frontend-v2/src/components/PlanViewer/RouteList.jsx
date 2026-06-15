import { useState } from 'react';
import { DEMO_FARMS, DEMO_DEMAND_POINTS } from '@/utils/demoFixtures';

function resolveStopName(stop) {
  if (stop.demand_point_id) {
    const dp = DEMO_DEMAND_POINTS.find(d => d.id === stop.demand_point_id);
    return dp ? dp.name : stop.demand_point_id;
  }
  if (stop.label) {
    const farm = DEMO_FARMS.find(f => f.id === stop.label);
    return farm ? farm.name : stop.label;
  }
  return `Stop ${stop.sequence + 1}`;
}

function stopType(stop) {
  return stop.demand_point_id ? 'MANDI DROP-OFF' : 'FARM PICKUP';
}

export default function RouteList({ routes = [] }) {
  const [expanded, setExpanded] = useState({});

  function toggle(idx) {
    setExpanded(prev => ({ ...prev, [idx]: !prev[idx] }));
  }

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
              style={{ borderTop: idx === 0 ? 'none' : '1px solid var(--border)' }}
            >
              <button
                type="button"
                onClick={() => toggle(idx)}
                className="w-full px-5 py-3 flex justify-between items-center text-left"
                style={{ background: 'none', border: 'none', cursor: 'pointer' }}
              >
                <div>
                  <p
                    className="font-syne font-bold text-paper"
                    style={{ fontSize: '13px', letterSpacing: '0.05em' }}
                  >
                    Truck {r.truckId || `#${idx + 1}`}
                  </p>
                  <p className="font-mono text-muted text-[11px] mt-1">
                    {r.stops?.length || 0} stops
                    {r.distance_km ? ` · ${r.distance_km} km` : ''}
                    {r.duration_minutes ? ` · ~${Math.round(r.duration_minutes / 60)}h` : ''}
                  </p>
                </div>
                <div className="text-right flex items-center gap-3">
                  {r.loadKg > 0 && (
                    <p className="font-mono text-[12px]" style={{ color: 'var(--accent)' }}>
                      {r.loadKg.toLocaleString()} kg
                    </p>
                  )}
                  <span className="font-mono text-[11px]" style={{ color: 'var(--muted)' }}>
                    {expanded[idx] ? '▲' : '▼'}
                  </span>
                </div>
              </button>

              {expanded[idx] && (
                <div className="px-5 pb-3 space-y-2">
                  {(r.stops || []).map((stop, si) => (
                    <div
                      key={si}
                      className="flex items-start gap-3 py-2"
                      style={{ borderTop: '1px solid var(--border)' }}
                    >
                      <div
                        className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                        style={{
                          background: stop.demand_point_id ? '#581c87' : '#166534',
                          color: '#fff',
                          fontSize: '10px',
                          fontWeight: 700,
                        }}
                      >
                        {stop.sequence + 1}
                      </div>
                      <div className="flex-1">
                        <p className="font-mono text-[12px]" style={{ color: 'var(--text)' }}>
                          {resolveStopName(stop)}
                        </p>
                        <p className="font-mono text-[10px] mt-0.5" style={{ color: 'var(--muted)' }}>
                          {stopType(stop)}
                          {stop.load_kg ? ` · ${Math.round(stop.load_kg).toLocaleString()} kg` : ''}
                          {stop.eta_minutes_from_start != null ? ` · ETA +${stop.eta_minutes_from_start}min` : ''}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
