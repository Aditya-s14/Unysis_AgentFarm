const COMMITMENT_DAYS_BEFORE_HARVEST = 7;

function parseDate(iso) {
  const [y, m, d] = String(iso).split('-').map(Number);
  return new Date(y, m - 1, d);
}

function startOfDay(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

/** Haversine distance in km between two lat/lng points. */
export function haversineKm(lat1, lng1, lat2, lng2) {
  const R = 6371;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function nearestMandiId(farm, demandPoints) {
  if (!farm || !Array.isArray(demandPoints) || demandPoints.length === 0) return null;
  let best = demandPoints[0];
  let bestKm = haversineKm(farm.lat, farm.lng, best.lat, best.lng);
  for (let i = 1; i < demandPoints.length; i += 1) {
    const dp = demandPoints[i];
    const km = haversineKm(farm.lat, farm.lng, dp.lat, dp.lng);
    if (km < bestKm) {
      best = dp;
      bestKm = km;
    }
  }
  return best.id;
}

export function nearestMandiLabel(farm, demandPoints) {
  const id = nearestMandiId(farm, demandPoints);
  if (!id) return '—';
  const dp = demandPoints.find((d) => d.id === id);
  return dp?.name || id;
}

/**
 * Harvest window starts within 7 days (inclusive) of today.
 */
export function isCommitmentEligible(farm, today = new Date()) {
  if (!farm?.harvest_window_start) return false;
  const ref = startOfDay(today);
  const harvest = startOfDay(parseDate(farm.harvest_window_start));
  const daysUntil = Math.round((harvest - ref) / (24 * 60 * 60 * 1000));
  return daysUntil >= 0 && daysUntil <= COMMITMENT_DAYS_BEFORE_HARVEST;
}

export function listEligibleFarms(farms, today = new Date()) {
  return (farms || []).filter((f) => isCommitmentEligible(f, today));
}

export function daysUntilHarvest(farm, today = new Date()) {
  if (!farm?.harvest_window_start) return null;
  const ref = startOfDay(today);
  const harvest = startOfDay(parseDate(farm.harvest_window_start));
  return Math.round((harvest - ref) / (24 * 60 * 60 * 1000));
}
