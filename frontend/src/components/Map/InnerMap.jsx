import { MapContainer, TileLayer } from 'react-leaflet';
import FarmMarker from './FarmMarker';
import MandiMarker from './MandiMarker';
import RoutePolyline from './RoutePolyline';

const INDIA_CENTER = [20.5937, 78.9629];
const DEFAULT_ZOOM = 5;

/**
 * InnerMap — the actual react-leaflet map. Rendered client-side only
 * via dynamic import from MapView.jsx.
 */
export default function InnerMap({ farms = [], demandPoints = [], routes = [] }) {
  return (
    <MapContainer
      center={INDIA_CENTER}
      zoom={DEFAULT_ZOOM}
      scrollWheelZoom={true}
      style={{ width: '100%', height: '100%' }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {farms.map((farm) => (
        <FarmMarker key={farm.id} farm={farm} />
      ))}
      {demandPoints.map((dp) => (
        <MandiMarker key={dp.id} mandi={dp} />
      ))}
      {routes.map((route, idx) => (
        <RoutePolyline key={route.id || idx} route={route} />
      ))}
    </MapContainer>
  );
}
