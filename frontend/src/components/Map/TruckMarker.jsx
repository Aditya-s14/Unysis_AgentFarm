import { CircleMarker, Popup } from 'react-leaflet';
import { displayTruckId } from '@/utils/truckDisplay';

function colorsForStatus(status) {
  switch (status) {
    case 'deviating':
      return { stroke: '#FF4444', fill: '#FF4444' };
    case 'stale':
      return { stroke: '#8A9E8C', fill: '#8A9E8C' };
    case 'on_route':
      return { stroke: '#4CAF50', fill: '#4CAF50' };
    default:
      return { stroke: '#F5A623', fill: '#F5A623' };
  }
}

/**
 * Live truck GPS marker on the map.
 */
export default function TruckMarker({ position, isSelected = false }) {
  if (!position?.lat || !position?.lng) return null;
  const c = colorsForStatus(position.status);
  const label = displayTruckId(position.truck_id);
  const radius = isSelected ? 14 : 11;

  return (
    <CircleMarker
      center={[position.lat, position.lng]}
      radius={radius}
      pathOptions={{
        color: c.stroke,
        fillColor: c.fill,
        fillOpacity: 0.9,
        weight: isSelected ? 3 : 2,
      }}
    >
      <Popup>
        <div style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 12 }}>
          <p style={{ margin: 0, fontWeight: 700, color: 'var(--accent)' }}>{label}</p>
          <p style={{ margin: '4px 0 0', color: 'var(--muted)' }}>
            Status: {(position.status || 'unknown').replace('_', ' ').toUpperCase()}
          </p>
          <p style={{ margin: '2px 0 0', color: 'var(--muted)' }}>
            Deviation: {position.deviation_km?.toFixed?.(1) ?? position.deviation_km} km
          </p>
        </div>
      </Popup>
    </CircleMarker>
  );
}
