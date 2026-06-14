import { CircleMarker, Popup } from 'react-leaflet';

const RISK_COLORS = {
  severe:  { color: '#b91c1c', fill: '#ef4444' },
  warning: { color: '#b45309', fill: '#f59e0b' },
  normal:  { color: '#1976D2', fill: '#2196F3' },
};

/** MandiMarker — renders a demand point (mandi/retailer) as a circle, coloured by stock risk. */
export default function MandiMarker({ mandi, riskLevel = 'normal' }) {
  if (!mandi?.location) return null;
  const { lat, lng } = mandi.location;
  const { color, fill } = RISK_COLORS[riskLevel] || RISK_COLORS.normal;
  return (
    <CircleMarker
      center={[lat, lng]}
      radius={12}
      pathOptions={{
        color,
        fillColor: fill,
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
          {riskLevel !== 'normal' && (
            <p style={{ margin: '4px 0 0', fontWeight: 700, color: riskLevel === 'severe' ? '#ef4444' : '#f59e0b' }}>
              {riskLevel === 'severe' ? '⚠ STOCK SHORTAGE' : '⚠ LOW STOCK'}
            </p>
          )}
        </div>
      </Popup>
    </CircleMarker>
  );
}
