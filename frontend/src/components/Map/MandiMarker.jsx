import { CircleMarker, Popup } from 'react-leaflet';

/** MandiMarker — renders a demand point (mandi/retailer) as an orange circle. */
export default function MandiMarker({ mandi }) {
  if (!mandi?.location) return null;
  const { lat, lng } = mandi.location;
  return (
    <CircleMarker
      center={[lat, lng]}
      radius={9}
      pathOptions={{ color: '#bf360c', fillColor: '#ef6c00', fillOpacity: 0.85 }}
    >
      <Popup>
        <div className="text-sm">
          <p className="font-semibold">{mandi.name || `Mandi ${mandi.id}`}</p>
          <p>ID: {mandi.id}</p>
          {mandi.type && <p>Type: {mandi.type}</p>}
          {mandi.base_demand_per_day && (
            <p>Daily demand: {mandi.base_demand_per_day} kg</p>
          )}
        </div>
      </Popup>
    </CircleMarker>
  );
}
