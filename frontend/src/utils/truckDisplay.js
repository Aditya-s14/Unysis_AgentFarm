import { ARROW, ELLIPSIS } from '@/utils/uiChars';

export const ROUTE_ARROW = ARROW;

/** Strip corrupted UTF-8 prefixes (truck emoji / DYSS mojibake). */
function stripCorruptedPrefix(id) {
  let s = id;
  s = s.replace(/^DY[SŠ]{2}\s*/gi, '');
  s = s.replace(/^DYSS\s*/gi, '');
  s = s.replace(/^truck\s+/gi, '');
  s = s.replace(/\btruck\s+/gi, '');
  // Truck emoji mojibake: 
  s = s.replace(/^\u00f0\u0178\u0161\u0161\s*/i, '');
  s = s.replace(/^[\u00c0-\u024f\s]+(?=TR-)/i, '');
  return s.trim();
}

/**
 * Display-only truck ID (backend IDs unchanged).
 * Normalises tr-004 → TR-004.
 */
export function displayTruckId(rawId) {
  if (rawId == null || rawId === '') return 'TR-???';

  let id = stripCorruptedPrefix(String(rawId).trim());

  const trMatch = id.match(/TR-(\d{1,4})/i);
  if (trMatch) {
    return `TR-${trMatch[1].padStart(3, '0')}`;
  }

  id = id.replace(/^tr[-_\s]*/i, '');
  const digits = id.match(/(\d{1,4})/);
  if (digits) {
    return `TR-${digits[1].padStart(3, '0')}`;
  }

  if (/^TR-/i.test(id)) {
    return id.toUpperCase();
  }

  return id.toUpperCase();
}

/**
 * Build ordered route stop labels from farm/mandi stop lists.
 */
export function buildRouteLabel(farmNames, dpNames) {
  const parts = [...(farmNames || []), ...(dpNames || [])].filter(Boolean);
  return parts.join(` ${ROUTE_ARROW} `);
}

export function truncateRoute(label, maxLen = 52) {
  if (!label || label.length <= maxLen) return { short: label, truncated: false };
  return { short: `${label.slice(0, maxLen).trim()}${ELLIPSIS}`, truncated: true };
}
