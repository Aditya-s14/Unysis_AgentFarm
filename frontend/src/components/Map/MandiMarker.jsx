import { CircleMarker, Popup } from 'react-leaflet';

/** MandiMarker — renders a demand point (mandi/retailer) as a bright blue circle. */
export default function MandiMarker({ mandi }) {
  if (!mandi?.location) return null;
  const { lat, lng } = mandi.location;
  return (
    <CircleMarker
      center={[lat, lng]}
      radius={12}
      pathOptions={{
        color: '#1976D2',
        fillColor: '#2196F3',
        fillOpacity: 0.85,
        weight: 2,
      }}
    >
      <Popup>
        <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 12 }}>
          <p style={{ margin: 0, color: 'var(--accent)', fontFamily: 'Syne, sans-serif', fontWeight: 700 }}>
            {mandi.name || `Mandi ${mandi.id}`}
          </p>
          <p style={{ margin: '4px 0 0', color: 'var(--muted)' }}>ID: {mandi.id}</p>
          {mandi.type && (
            <p style={{ margin: '2px 0 0', color: 'var(--muted)' }}>Type: {mandi.type}</p>
          )}
          {mandi.base_demand_per_day && (
            <p style={{ margin: '2px 0 0', color: 'var(--muted)' }}>
              Daily demand: <span style={{ color: 'var(--text)' }}>{mandi.base_demand_per_day} kg</span>
            </p>
          )}
        </div>
      </Popup>
    </CircleMarker>
  );
}
