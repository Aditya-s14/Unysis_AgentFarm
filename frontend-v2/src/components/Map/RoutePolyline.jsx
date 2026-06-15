import { CircleMarker, Polyline, Popup } from 'react-leaflet';

const ACCENT = '#F5A623';
const FADED  = '#8A9E8C';

const RISK_COLORS = {
  severe:  '#E74C3C',
  warning: 'var(--harvest-gold)',
};

/**
 * RoutePolyline — draws a single truck route on the Leaflet map.
 *
 * Props:
 *   route              Route object with stops[], truckId, distance_km.
 *   isSelected         This truck is the active selection → thick accent line.
 *   isDeemphasized     Another truck is selected → thin, faded line.
 *   weatherRiskByFarm  { [farmId]: 'severe' | 'warning' | 'normal' } for weather badges.
 */
export default function RoutePolyline({
  route,
  isSelected = false,
  isDeemphasized = false,
  weatherRiskByFarm = {},
}) {
  if (!route?.stops || route.stops.length < 2) return null;

  // Road-snapped geometry from the backend (T7); straight stop-to-stop
  // lines when no routing provider was available.
  const positions = Array.isArray(route.geometry) && route.geometry.length >= 2
    ? route.geometry
    : route.stops.map((s) => [s.lat, s.lng]);

  let pathOptions;
  if (isSelected) {
    pathOptions = { color: ACCENT, weight: 5, opacity: 1.0 };
  } else if (isDeemphasized) {
    pathOptions = { color: FADED,  weight: 1, opacity: 0.2 };
  } else {
    pathOptions = { color: ACCENT, weight: 3, opacity: 0.85 };
  }

  const distKm = route.distance_km != null ? Math.abs(route.distance_km) : null;

  const riskStops = route.stops.filter((s) => {
    if (s.demand_point_id) return false;
    const risk = weatherRiskByFarm[s.label];
    return risk === 'severe' || risk === 'warning';
  });

  return (
    <>
      <Polyline positions={positions} pathOptions={pathOptions}>
        <Popup>
        <div style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 12 }}>
          <p style={{ margin: 0, color: ACCENT, fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: 700 }}>
              Truck {route.truckId || route.id}
            </p>
            <p style={{ margin: '4px 0 0', color: 'var(--muted)' }}>{route.stops.length} stops</p>
            {distKm != null && (
              <p style={{ margin: '2px 0 0', color: 'var(--muted)' }}>
                Distance: <span style={{ color: 'var(--text)' }}>~{distKm.toFixed(0)} km</span>
              </p>
            )}
          </div>
        </Popup>
      </Polyline>

      {riskStops.map((s, i) => {
        const risk = weatherRiskByFarm[s.label];
        const color = RISK_COLORS[risk] || ACCENT;
        return (
          <CircleMarker
            key={`risk-stop-${i}`}
            center={[s.lat, s.lng]}
            radius={6}
            pathOptions={{ color, fillColor: color, fillOpacity: 0.9, weight: 1.5 }}
          >
            <Popup>
              <div style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 11 }}>
                <p style={{ margin: 0, color, fontWeight: 700 }}>{risk === 'severe' ? 'SEVERE RISK' : 'WEATHER WARNING'}</p>
                <p style={{ margin: '2px 0 0', color: 'var(--muted)' }}>{s.label}</p>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}
