import { getRun } from '@/api/client';
import { DEMO_FARMS } from '@/utils/demoFixtures';

/** Return plan UUID from cached run or fetch GET /api/run/{runId}. */
export async function resolvePlanId(cached, runId) {
  const fromCache = cached?.plan?.id;
  if (fromCache) return String(fromCache);
  if (!runId) {
    throw new Error('No plan_id available — run a scenario first');
  }
  const runResp = await getRun(runId);
  if (!runResp?.id) {
    throw new Error('Could not resolve plan_id for this run');
  }
  return String(runResp.id);
}

/** Proportional share of optimized waste attributed to this mandi. */
export function estimateWasteShare(kpis, mandiIncoming, totalIncoming) {
  const totalWaste = Number(kpis?.optimized_waste_kg ?? 0);
  if (totalWaste <= 0 || mandiIncoming <= 0 || totalIncoming <= 0) return 0;
  return (totalWaste * mandiIncoming) / totalIncoming;
}

/** Dominant crop from farm stops on routes delivering to this mandi. */
export function resolveDominantCrop(mandiId, rawRoutes, farms) {
  const farmList = Array.isArray(farms) && farms.length ? farms : DEMO_FARMS;
  const farmById = new Map(farmList.map((f) => [f.id, f]));
  const counts = {};

  (rawRoutes || []).forEach((route) => {
    const servesMandi = (route.stops || []).some((s) => s.demand_point_id === mandiId);
    if (!servesMandi) return;
    (route.stops || []).forEach((s) => {
      if (s.demand_point_id || !s.label) return;
      const crop = farmById.get(s.label)?.crop_type;
      if (crop) counts[crop] = (counts[crop] || 0) + 1;
    });
  });

  const entries = Object.entries(counts);
  if (entries.length === 0) {
    return farmList[0]?.crop_type || 'tomato';
  }
  entries.sort((a, b) => b[1] - a[1]);
  return entries[0][0];
}

/** Max predicted delivery duration (hours) for routes serving this mandi. */
export function resolveDeliveryPredictedHours(mandiId, rawRoutes) {
  let maxHours = 0;
  (rawRoutes || []).forEach((route) => {
    const servesMandi = (route.stops || []).some((s) => s.demand_point_id === mandiId);
    if (!servesMandi) return;
    const minutes = Number(route.duration_minutes);
    if (Number.isFinite(minutes) && minutes > 0) {
      maxHours = Math.max(maxHours, minutes / 60);
    } else {
      const km = Number(route.distance_km);
      if (Number.isFinite(km) && km > 0) {
        maxHours = Math.max(maxHours, km / 40);
      }
    }
  });
  return maxHours > 0 ? Math.round(maxHours * 100) / 100 : 4;
}

function resolveDemandPredicted(mandiRow, cached) {
  const forecast = cached?.demand_forecast?.[mandiRow.id];
  if (Array.isArray(forecast) && forecast.length > 0) {
    return Math.round(Number(forecast[0]));
  }
  return mandiRow.expectedDemand;
}

function computeTotalIncoming(rawRoutes) {
  const byMandi = {};
  (rawRoutes || []).forEach((route) => {
    const farmStops = (route.stops || []).filter((s) => !s.demand_point_id && s.label);
    const dpStops = (route.stops || []).filter((s) => s.demand_point_id);
    const farmLoad = farmStops.reduce(
      (sum, s) => sum + (s.load_kg != null && s.load_kg > 0 ? Number(s.load_kg) : 0),
      0,
    );
    dpStops.forEach((stop) => {
      const dpId = stop.demand_point_id;
      let loadKg = 0;
      if (stop.load_kg != null && stop.load_kg > 0) {
        loadKg = Number(stop.load_kg);
      } else if (dpStops.length > 0) {
        loadKg = farmLoad / dpStops.length;
      }
      byMandi[dpId] = (byMandi[dpId] || 0) + loadKg;
    });
  });
  return Object.values(byMandi).reduce((s, v) => s + v, 0);
}

/**
 * Build outcome fields for modal preview and API submit (without plan_id).
 */
export function buildMandiOutcomeDraft({
  cached,
  mandiRow,
  rawRoutes,
  farms,
  actualOverrides = {},
}) {
  const demandPredicted = resolveDemandPredicted(mandiRow, cached);
  const demandActual = actualOverrides.demand_actual != null
    ? Number(actualOverrides.demand_actual)
    : mandiRow.incomingSupply;

  const totalIncoming = computeTotalIncoming(rawRoutes);
  const wastePredicted = estimateWasteShare(
    cached?.kpis,
    mandiRow.incomingSupply,
    totalIncoming,
  );
  const defaultWasteActual = Math.max(0, mandiRow.expectedDemand - mandiRow.incomingSupply);
  const wasteActual = actualOverrides.waste_kg_actual != null
    ? Number(actualOverrides.waste_kg_actual)
    : defaultWasteActual;

  const deliveryPredicted = resolveDeliveryPredictedHours(mandiRow.id, rawRoutes);
  const deliveryActual = actualOverrides.delivery_time_actual_hours != null
    ? Number(actualOverrides.delivery_time_actual_hours)
    : Math.round((deliveryPredicted + 0.2) * 100) / 100;

  const dayOfWeek = new Date().toLocaleDateString('en-US', { weekday: 'long' }).toLowerCase();
  const cropType = resolveDominantCrop(mandiRow.id, rawRoutes, farms);

  return {
    waste_kg_predicted: Math.round(wastePredicted * 10) / 10,
    waste_kg_actual: Math.round(wasteActual * 10) / 10,
    delivery_time_predicted_hours: deliveryPredicted,
    delivery_time_actual_hours: deliveryActual,
    demand_predicted: demandPredicted,
    demand_actual: demandActual,
    demand_point_id: mandiRow.id,
    crop_type: cropType,
    day_of_week: dayOfWeek,
    notes: actualOverrides.notes
      ?? `UI delivery confirmation for ${mandiRow.name}`,
  };
}

/** Full PlanOutcome payload for POST /api/outcome/log. */
export async function buildMandiOutcomePayload({
  cached,
  mandiRow,
  rawRoutes,
  farms,
  runId,
  actualOverrides = {},
}) {
  const plan_id = await resolvePlanId(cached, runId);
  const draft = buildMandiOutcomeDraft({
    cached,
    mandiRow,
    rawRoutes,
    farms,
    actualOverrides,
  });
  return { plan_id, ...draft };
}
