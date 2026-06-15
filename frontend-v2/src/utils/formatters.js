/**
 * Display-layer formatting helpers.
 * Kept pure and side-effect-free so they can be used anywhere in the UI.
 */

/** Format a weight in kilograms (auto-switches to tonnes past 1000 kg). */
export function formatKg(kg) {
  if (kg === null || kg === undefined || Number.isNaN(kg)) return '--';
  const value = Number(kg);
  if (Math.abs(value) >= 1000) {
    return `${(value / 1000).toFixed(2)} t`;
  }
  return `${value.toFixed(1)} kg`;
}

/** Format an INR currency value with the rupee symbol and Indian locale grouping. */
export function formatCurrency(amount) {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return '--';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(amount));
}

/** Format a 0-1 or 0-100 value as a percentage string. */
export function formatPercentage(value, { alreadyPercent = false, digits = 1 } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--';
  const pct = alreadyPercent ? Number(value) : Number(value) * 100;
  return `${pct.toFixed(digits)}%`;
}

/** Format a millisecond duration as a short human string. */
export function formatDuration(ms) {
  if (ms === null || ms === undefined || Number.isNaN(ms)) return '--';
  const v = Number(ms);
  if (v < 1000) return `${v.toFixed(0)} ms`;
  if (v < 60_000) return `${(v / 1000).toFixed(2)} s`;
  const minutes = Math.floor(v / 60_000);
  const seconds = Math.round((v % 60_000) / 1000);
  return `${minutes}m ${seconds}s`;
}
