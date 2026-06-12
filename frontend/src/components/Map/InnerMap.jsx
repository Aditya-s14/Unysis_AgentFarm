import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import FarmMarker from './FarmMarker';
import MandiMarker from './MandiMarker';
import RoutePolyline from './RoutePolyline';
import TruckMarker from './TruckMarker';

// Centred on the Bengaluru / Karnataka tomato belt that the demo fixture uses.
const MAP_CENTER = [13.1, 77.7];
const DEFAULT_ZOOM = 9;

/**
 * FlyToController — headless component that calls map.flyTo() whenever
 * `coords` changes. Placed inside MapContainer so it can access the map
 * instance via useMap().
 */
function FlyToController({ coords }) {
  const map = useMap();
  useEffect(() => {
    if (coords) {
      map.flyTo(coords, 11, { animate: true, duration: 1.2 });
    }
  }, [coords, map]);
  return null;
}

/**
 * InnerMap — the actual react-leaflet map. Rendered client-side only
 * via dynamic import from MapView.jsx.
 *
 * Props:
 *   farms           Farm[]          Farm markers.
 *   demandPoints    DemandPoint[]   Mandi markers.
 *   routes          Route[]         Polyline routes; each has truckId and stops.
 *   selectedTruckId string | null   If set, highlights that truck's route and
 *                                   fades all others.
 */
export default function InnerMap({
  farms = [],
  demandPoints = [],
  routes = [],
  truckPositions = [],
  selectedTruckId = null,
  weatherRiskByFarm = {},
  weatherRiskByMandi = {},
}) {
  if (typeof window !== 'undefined' && (!Array.isArray(routes) || routes.length === 0)) {
    // eslint-disable-next-line no-console
    console.warn(
      '[InnerMap] No route polylines to draw — plan.route_plan.routes is empty/undefined. ' +
        'Markers will still render.',
    );
  }

  // Compute flyTo target: first stop of the selected truck's route.
  const flyCoords = useMemo(() => {
    if (!selectedTruckId) return null;
    const route = routes.find((r) => {
      const vid = r.truckId ?? r.vehicle_id ?? r.id;
      return vid === selectedTruckId;
    });
    const first = route?.stops?.[0];
    return first ? [first.lat, first.lng] : null;
  }, [selectedTruckId, routes]);

  const hasSelection = selectedTruckId != null;

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

      {/* Fly to selected truck's first stop */}
      {flyCoords && <FlyToController coords={flyCoords} />}

      {farms.map((farm) => (
        <FarmMarker key={farm.id} farm={farm} />
      ))}
      {demandPoints.map((dp) => (
        <MandiMarker key={dp.id} mandi={dp} riskLevel={weatherRiskByMandi[dp.id] || 'normal'} />
      ))}
      {(routes || []).map((route, idx) => {
        const vehicleId = route.truckId ?? route.vehicle_id ?? route.id;
        const routeKey = vehicleId || idx;
        const isSelected = hasSelection && vehicleId === selectedTruckId;
        const isDeemphasized = hasSelection && !isSelected;
        return (
          <RoutePolyline
            key={routeKey}
            route={route}
            isSelected={isSelected}
            isDeemphasized={isDeemphasized}
            weatherRiskByFarm={weatherRiskByFarm}
          />
        );
      })}
      {(truckPositions || []).map((pos) => (
        <TruckMarker
          key={`live-${pos.truck_id}`}
          position={pos}
          isSelected={hasSelection && pos.truck_id === selectedTruckId}
        />
      ))}
    </MapContainer>
  );
}
