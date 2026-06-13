const FALLBACK =
  'This route was optimised by OR-Tools to minimise total distance and spoilage risk.';

const SHORTAGE_LABELS = new Set(['CRITICAL SHORTAGE', 'SHORTAGE']);

function sortStops(stops) {
  return [...(stops || [])].sort((a, b) => (a.sequence ?? 0) - (b.sequence ?? 0));
}

function farmName(farmId, farmsById) {
  if (!farmId) return 'farm';
  const f = farmsById?.get?.(farmId) ?? farmsById?.[farmId];
  return f?.name || farmId;
}

function mandiName(dpId, mandiById) {
  if (!dpId) return 'mandi';
  const row = mandiById?.get?.(dpId) ?? mandiById?.[dpId];
  return row?.name || dpId;
}

function hasConsolidatedPickup(orderedStops) {
  let pendingFarms = 0;
  for (const s of orderedStops) {
    if (s.demand_point_id == null && s.label) {
      pendingFarms += 1;
    } else if (s.demand_point_id != null) {
      if (pendingFarms >= 2) return true;
      pendingFarms = 0;
    }
  }
  return false;
}

/**
 * Build a plain-English route justification from stop order and plan data.
 * Names come from farmsById / mandiById — never hardcoded.
 */
export function buildRouteExplanation({
  stops = [],
  atRiskMap = {},
  mandiById = null,
  farmsById = null,
}) {
  const ordered = sortStops(stops);
  const farmStops = ordered.filter((s) => s.demand_point_id == null && s.label);
  const dpStops = ordered.filter((s) => s.demand_point_id != null);

  if (farmStops.length === 0 && dpStops.length === 0) {
    return FALLBACK;
  }

  const resolveMandi = (id) => {
    if (!mandiById) return null;
    return mandiById.get ? mandiById.get(id) : mandiById[id];
  };

  const hasAtRisk = Object.keys(atRiskMap || {}).length > 0;
  const hasMandiRows = mandiById && (mandiById.size > 0 || Object.keys(mandiById).length > 0);

  if (!hasAtRisk && !hasMandiRows && farmStops.length === 0 && dpStops.length === 0) {
    return FALLBACK;
  }

  const parts = [];
  const farmCount = farmStops.length;
  const mandiCount = dpStops.length;

  if (farmCount > 0 && mandiCount > 0) {
    parts.push(
      `This route includes ${farmCount} farm pickup${farmCount !== 1 ? 's' : ''} `
      + `and ${mandiCount} mandi deliver${mandiCount !== 1 ? 'ies' : 'y'}.`,
    );
  } else if (farmCount > 0) {
    parts.push(`This route includes ${farmCount} farm pickup${farmCount !== 1 ? 's' : ''}.`);
  } else {
    parts.push(`This route includes ${mandiCount} mandi deliver${mandiCount !== 1 ? 'ies' : 'y'}.`);
  }

  let urgentId = null;
  let urgentHours = Infinity;
  farmStops.forEach((s) => {
    const h = atRiskMap[s.label]?.hours_until_spoilage;
    if (h != null && h < urgentHours) {
      urgentHours = h;
      urgentId = s.label;
    }
  });

  if (urgentId != null && Number.isFinite(urgentHours)) {
    parts.push(
      `${farmName(urgentId, farmsById)} prioritised first — shortest spoilage window (${Math.round(urgentHours)}h).`,
    );
  }

  if (hasConsolidatedPickup(ordered)) {
    parts.push('Consolidated pickup to reduce distance before mandi delivery.');
  }

  dpStops.forEach((s) => {
    const row = resolveMandi(s.demand_point_id);
    if (row && SHORTAGE_LABELS.has(row.statusLabel)) {
      parts.push(
        `Directly serves ${mandiName(s.demand_point_id, mandiById)}, which has high shortage `
        + `(${Math.round(row.fulfilmentPct)}% fulfilment).`,
      );
    }
  });

  const hasDetail = parts.length > 1
    || (urgentId != null && Number.isFinite(urgentHours))
    || hasConsolidatedPickup(ordered)
    || dpStops.some((s) => SHORTAGE_LABELS.has(resolveMandi(s.demand_point_id)?.statusLabel));

  if (!hasDetail) {
    return parts.length > 0 ? `${parts[0]} ${FALLBACK}` : FALLBACK;
  }

  return parts.join(' ');
}
