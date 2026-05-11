import { Polyline, Popup } from 'react-leaflet';

/**
 * RoutePolyline — saffron line linking the ordered stops of a single truck route.
 * Expects `route.stops` to be an array of {lat, lng}.
 */
export default function RoutePolyline({ route }) {
  if (!route?.stops || route.stops.length < 2) return null;
  const positions = route.stops.map((s) => [s.lat, s.lng]);
  return (
    <Polyline
      positions={positions}
      pathOptions={{ color: '#F5A623', weight: 3, opacity: 0.85 }}
    >
      <Popup>
        <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 12 }}>
          <p style={{ margin: 0, color: 'var(--accent)', fontFamily: 'Syne, sans-serif', fontWeight: 700 }}>
            Truck {route.truckId || route.id}
          </p>
          <p style={{ margin: '4px 0 0', color: 'var(--muted)' }}>{route.stops.length} stops</p>
          {route.distance_km && (
            <p style={{ margin: '2px 0 0', color: 'var(--muted)' }}>
              Distance: <span style={{ color: 'var(--text)' }}>{route.distance_km} km</span>
            </p>
          )}
        </div>
      </Popup>
    </Polyline>
  );
}
