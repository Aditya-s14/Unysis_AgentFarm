import { MapContainer, TileLayer } from 'react-leaflet';
import FarmMarker from './FarmMarker';
import MandiMarker from './MandiMarker';
import RoutePolyline from './RoutePolyline';

// Centred on the Bengaluru / Karnataka tomato belt that the demo fixture uses.
const MAP_CENTER = [13.1, 77.7];
const DEFAULT_ZOOM = 9;

/**
 * InnerMap — the actual react-leaflet map. Rendered client-side only
 * via dynamic import from MapView.jsx.
 *
 * Uses CartoDB Dark Matter tiles so the map blends into the mission-control
 * aesthetic. When ``routes`` is empty we still draw markers (with a
 * console.warn for debugging the polylines pathway).
 */
export default function InnerMap({ farms = [], demandPoints = [], routes = [] }) {
  if (typeof window !== 'undefined' && (!Array.isArray(routes) || routes.length === 0)) {
    // eslint-disable-next-line no-console
    console.warn(
      '[InnerMap] No route polylines to draw — plan.route_plan.routes is empty/undefined. ' +
        'Markers will still render.',
    );
  }

  return (
    <MapContainer
      center={MAP_CENTER}
      zoom={DEFAULT_ZOOM}
      scrollWheelZoom={true}
      style={{ width: '100%', height: '100%', background: 'var(--bg)' }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        subdomains="abcd"
      />
      {farms.map((farm) => (
        <FarmMarker key={farm.id} farm={farm} />
      ))}
      {demandPoints.map((dp) => (
        <MandiMarker key={dp.id} mandi={dp} />
      ))}
      {(routes || []).map((route, idx) => (
        <RoutePolyline key={route.id || idx} route={route} />
      ))}
    </MapContainer>
  );
}
