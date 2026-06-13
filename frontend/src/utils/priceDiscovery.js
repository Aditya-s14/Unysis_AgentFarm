import { formatCurrency } from '@/utils/formatters';

/** Haversine distance in km (mirrors commitmentEligibility). */
export function haversineKm(lat1, lng1, lat2, lng2) {
  const R = 6371;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function nearestDemandPointByType(farm, demandPoints, type) {
  if (!farm || !Array.isArray(demandPoints)) return null;
  const candidates = demandPoints.filter((dp) => (dp.point_type || dp.type) === type);
  if (candidates.length === 0) return null;
  let best = candidates[0];
  let bestKm = haversineKm(farm.lat, farm.lng, best.lat, best.lng);
  for (let i = 1; i < candidates.length; i += 1) {
    const dp = candidates[i];
    const km = haversineKm(farm.lat, farm.lng, dp.lat, dp.lng);
    if (km < bestKm) {
      best = dp;
      bestKm = km;
    }
  }
  return best;
}

/** Display ₹/kg using INR formatter. */
export function formatPricePerKg(amount) {
  if (amount == null || Number.isNaN(Number(amount))) return '--';
  return `${formatCurrency(amount)}/kg`;
}

export function formatPremiumPct(pct) {
  if (pct == null || Number.isNaN(Number(pct))) return '';
  const n = Number(pct);
  return n > 0 ? `+${n.toFixed(1)}%` : `${n.toFixed(1)}%`;
}
