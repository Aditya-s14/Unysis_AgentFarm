import { Polyline, Popup } from 'react-leaflet';

const ACCENT = '#F5A623';
const FADED  = '#8A9E8C';

/**
 * RoutePolyline — draws a single truck route on the Leaflet map.
 *
 * Props:
 *   route           Route object with stops[], truckId, distance_km.
 *   isSelected      This truck is the active selection → thick accent line.
 *   isDeemphasized  Another truck is selected → thin, faded line.
 *   (both false)    Normal state → standard saffron line.
 */
export default function RoutePolyline({ route, isSelected = false, isDeemphasized = false }) {
  if (!route?.stops || route.stops.length < 2) return null;

  const positions = route.stops.map((s) => [s.lat, s.lng]);

  let pathOptions;
  if (isSelected) {
    pathOptions = { color: ACCENT, weight: 5, opacity: 1.0 };
  } else if (isDeemphasized) {
    pathOptions = { color: FADED,  weight: 1, opacity: 0.2 };
  } else {
    pathOptions = { color: ACCENT, weight: 3, opacity: 0.85 };
  }

  const distKm = route.distance_km != null ? Math.abs(route.distance_km) : null;

  return (
    <Polyline positions={positions} pathOptions={pathOptions}>
      <Popup>
        <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 12 }}>
          <p style={{ margin: 0, color: ACCENT, fontFamily: 'Syne, sans-serif', fontWeight: 700 }}>
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
  );
}
