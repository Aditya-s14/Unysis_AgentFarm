import { Polyline, Popup } from 'react-leaflet';

/**
 * RoutePolyline — draws a truck route as a line connecting its ordered stops.
 * Expects `route.stops` to be an array of {lat, lng} objects.
 */
export default function RoutePolyline({ route }) {
  if (!route?.stops || route.stops.length < 2) return null;
  const positions = route.stops.map((s) => [s.lat, s.lng]);
  return (
    <Polyline positions={positions} pathOptions={{ color: '#5e35b1', weight: 3, opacity: 0.8 }}>
      <Popup>
        <div className="text-sm">
          <p className="font-semibold">Truck {route.truckId || route.id}</p>
          <p>{route.stops.length} stops</p>
          {route.distance_km && <p>Distance: {route.distance_km} km</p>}
        </div>
      </Popup>
    </Polyline>
  );
}
