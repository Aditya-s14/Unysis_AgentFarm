import { CircleMarker, Popup } from 'react-leaflet';

/**
 * FarmMarker — renders a single farm as a green circle.
 * Uses CircleMarker to avoid the well-known Leaflet default-icon SSR pitfall.
 */
export default function FarmMarker({ farm }) {
  if (!farm?.location) return null;
  const { lat, lng } = farm.location;
  return (
    <CircleMarker
      center={[lat, lng]}
      radius={8}
      pathOptions={{ color: '#1b5e20', fillColor: '#2e7d32', fillOpacity: 0.85 }}
    >
      <Popup>
        <div className="text-sm">
          <p className="font-semibold">{farm.name || `Farm ${farm.id}`}</p>
          <p>ID: {farm.id}</p>
          {farm.crop_type && <p>Crop: {farm.crop_type}</p>}
          {farm.acreage && <p>Acreage: {farm.acreage}</p>}
        </div>
      </Popup>
    </CircleMarker>
  );
}
