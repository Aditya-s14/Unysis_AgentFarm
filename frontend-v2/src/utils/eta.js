export function computeETA(distanceKm, startHour = 6, avgSpeedKmh = 40) {
  if (!distanceKm || distanceKm <= 0) return 'TBD';
  const totalMin = Math.round((distanceKm / avgSpeedKmh) * 60);
  const etaTotalMin = startHour * 60 + totalMin;
  const h = Math.floor(etaTotalMin / 60) % 24;
  const m = etaTotalMin % 60;
  const period = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 || 12;
  return `${h12}:${m.toString().padStart(2, '0')} ${period}`;
}

export function etaFromMinutes(etaMinutesFromStart, depotDepartHour = 6) {
  if (etaMinutesFromStart == null) return null;
  const total = depotDepartHour * 60 + etaMinutesFromStart;
  const h = Math.floor(total / 60) % 24;
  const m = total % 60;
  const period = h >= 12 ? 'PM' : 'AM';
  return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${period}`;
}

export function minutesUntilETA(etaMinutesFromStart, depotDepartHour = 6) {
  if (etaMinutesFromStart == null) return null;
  const depotDepartMs = new Date().setHours(depotDepartHour, 0, 0, 0);
  const etaAbsoluteMs = depotDepartMs + etaMinutesFromStart * 60 * 1000;
  return Math.round((etaAbsoluteMs - Date.now()) / 60000);
}
