import { CircleMarker, Popup } from 'react-leaflet';

/**
 * FarmMarker — renders a single farm as a coloured circle on the dark map.
 * Status colours follow risk_level: high=red, medium=orange, low=green.
 * Falls back to neutral green if no risk info is present.
 */
function colorForRisk(risk) {
  switch ((risk || '').toLowerCase()) {
    case 'severe':
    case 'high':   return { stroke: '#E74C3C', fill: '#E74C3C' };
    case 'warning':
    case 'medium': return { stroke: 'var(--harvest-gold)', fill: 'var(--harvest-gold)' };
    case 'normal':
    case 'low':    return { stroke: '#22A06B', fill: '#22A06B' };
    default:       return { stroke: '#22A06B', fill: '#22A06B' };
  }
}

export default function FarmMarker({ farm }) {
  if (!farm?.location) return null;
  const { lat, lng } = farm.location;
  const c = colorForRisk(farm.risk_level);
  return (
    <CircleMarker
      center={[lat, lng]}
      radius={10}
      pathOptions={{
        color: c.stroke,
        fillColor: c.fill,
        fillOpacity: 0.85,
        weight: 2,
      }}
    >
      <Popup>
        <div style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 12 }}>
          <p style={{ margin: 0, color: 'var(--accent)', fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: 700 }}>
            {farm.name || `Farm ${farm.id}`}
          </p>
          <p style={{ margin: '4px 0 0', color: 'var(--muted)' }}>ID: {farm.id}</p>
          {farm.crop_type && (
            <p style={{ margin: '2px 0 0', color: 'var(--muted)' }}>Crop: {farm.crop_type}</p>
          )}
          {farm.acreage && (
            <p style={{ margin: '2px 0 0', color: 'var(--muted)' }}>Acreage: {farm.acreage}</p>
          )}
          {farm.risk_level && (
            <p style={{ margin: '2px 0 0', color: c.fill }}>Risk: {farm.risk_level}</p>
          )}
        </div>
      </Popup>
    </CircleMarker>
  );
}
