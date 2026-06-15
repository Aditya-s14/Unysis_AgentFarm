import { DEMO_DEMAND_POINTS, DEMO_FARMS } from '@/utils/demoFixtures';

let _stockFallbackWarned = false;

export function getDemandPointsFromCache(cached) {
  if (Array.isArray(cached?.demand_points) && cached.demand_points.length > 0) {
    return cached.demand_points;
  }
  const demoById = new Map(DEMO_DEMAND_POINTS.map((d) => [d.id, d]));
  const ids = new Set();
  (cached?.plan?.route_plan?.routes || []).forEach((r) => {
    (r.stops || []).forEach((s) => {
      if (s.demand_point_id) ids.add(s.demand_point_id);
    });
  });
  if (ids.size === 0) return [];
  return [...ids].map((id) => demoById.get(id) || { id, name: id, base_demand_per_day: 0 });
}

function resolveExpectedDemand(dp, cached) {
  const forecast = cached?.demand_forecast?.[dp.id];
  if (Array.isArray(forecast) && forecast.length > 0) {
    return Math.round(Number(forecast[0]));
  }
  return Math.round(Number(dp.base_demand_per_day_kg ?? dp.base_demand_per_day ?? 0));
}

function resolveCurrentStock(dp) {
  const demo = DEMO_DEMAND_POINTS.find((d) => d.id === dp.id);
  const raw = dp.current_stock_kg ?? dp.current_stock
    ?? demo?.current_stock_kg ?? demo?.current_stock;
  if (raw == null || raw === undefined) {
    if (typeof window !== 'undefined' && !_stockFallbackWarned) {
      // eslint-disable-next-line no-console
      console.warn(
        '[MANDI] current_stock_kg missing on demand points — assuming 0 for all mandis',
      );
      _stockFallbackWarned = true;
    }
    return 0;
  }
  return Math.max(0, Number(raw));
}

function computeIncomingByMandi(rawRoutes, atRiskMap) {
  const m = {};
  rawRoutes.forEach((route) => {
    const truckId = route.truck_id;
    if (!truckId) return;

    const farmStops = (route.stops || []).filter((s) => !s.demand_point_id && s.label);
    const dpStops = (route.stops || []).filter((s) => s.demand_point_id);

    const farmLoadFromStops = farmStops.reduce(
      (sum, s) => sum + (s.load_kg != null && s.load_kg > 0 ? Number(s.load_kg) : 0),
      0,
    );
    const farmLoadFromRisk = farmStops.reduce(
      (sum, s) => sum + (atRiskMap[s.label]?.kg_at_risk ?? 0),
      0,
    );
    const routeFarmLoad = farmLoadFromStops > 0 ? farmLoadFromStops : farmLoadFromRisk;

    dpStops.forEach((stop) => {
      const dpId = stop.demand_point_id;
      let loadKg = 0;
      if (stop.load_kg != null && stop.load_kg > 0) {
        loadKg = Number(stop.load_kg);
      } else if (dpStops.length > 0) {
        loadKg = routeFarmLoad / dpStops.length;
      }

      if (!m[dpId]) m[dpId] = { incomingKg: 0, trucks: [] };
      m[dpId].incomingKg += loadKg;
      m[dpId].trucks.push({ truck_id: truckId, load_kg: Math.round(loadKg) });
    });
  });
  return m;
}

function getFulfilmentStatus(fulfilmentPct) {
  if (fulfilmentPct < 50) return { label: 'CRITICAL SHORTAGE', color: 'var(--red-risk)' };
  if (fulfilmentPct < 80) return { label: 'SHORTAGE', color: 'var(--red-risk)' };
  if (fulfilmentPct < 100) return { label: 'NEARLY MET', color: 'var(--harvest-gold)' };
  if (fulfilmentPct <= 110) return { label: 'SUPPLY MET', color: 'var(--green-ok)' };
  return { label: 'EXCESS', color: 'var(--blue-mandi)' };
}

function fulfilmentBarColor(pct) {
  if (pct > 100) return 'var(--green-ok)';
  if (pct >= 80) return 'var(--harvest-gold)';
  return 'var(--red-risk)';
}

export function buildMandiFulfilmentRows(cached, rawRoutes, demandPoints, atRiskMap) {
  const incomingMap = computeIncomingByMandi(rawRoutes, atRiskMap);

  return demandPoints.map((dp) => {
    const expectedDemand = resolveExpectedDemand(dp, cached);
    const currentStock = resolveCurrentStock(dp);
    const usableStock = currentStock;
    const incoming = incomingMap[dp.id] || { incomingKg: 0, trucks: [] };
    const incomingSupply = Math.round(incoming.incomingKg);
    const totalAvailable = usableStock + incomingSupply;
    const netBalance = totalAvailable - expectedDemand;
    const fulfilmentPct = expectedDemand > 0
      ? Math.min(200, Math.max(0, (totalAvailable / expectedDemand) * 100))
      : 0;
    const shortageKg = Math.max(0, -netBalance);
    const excessKg = Math.max(0, netBalance);
    const status = getFulfilmentStatus(fulfilmentPct);

    return {
      id: dp.id,
      name: dp.name || dp.id,
      expectedDemand,
      currentStock,
      incomingSupply,
      usableStock,
      totalAvailable,
      netBalance,
      fulfilmentPct: Math.round(fulfilmentPct * 10) / 10,
      shortageKg,
      excessKg,
      statusLabel: status.label,
      statusColor: status.color,
      barColor: fulfilmentBarColor(fulfilmentPct),
      incomingTrucks: incoming.trucks,
    };
  });
}

export function summarizeMandiFulfilment(rows) {
  return {
    totalExpected: rows.reduce((s, r) => s + r.expectedDemand, 0),
    totalStock: rows.reduce((s, r) => s + r.currentStock, 0),
    totalIncoming: rows.reduce((s, r) => s + r.incomingSupply, 0),
    totalAvailable: rows.reduce((s, r) => s + r.totalAvailable, 0),
    netShortage: rows.reduce((s, r) => s + r.shortageKg, 0),
    mandisCovered: rows.filter(
      (r) => r.statusLabel === 'SUPPLY MET' || r.statusLabel === 'EXCESS',
    ).length,
    mandiCount: rows.length,
  };
}

export function buildSupplySuggestions(rows, cached, atRiskMap, rawRoutes) {
  const suggestions = [];
  const shortRows = rows.filter((r) => r.shortageKg > 0);
  const excessRows = rows.filter((r) => r.excessKg > 0).sort((a, b) => b.excessKg - a.excessKg);
  const usedDonorIds = new Set();

  shortRows.forEach((shortM) => {
    const donor = excessRows.find((e) => e.excessKg > 0 && !usedDonorIds.has(e.id));
    if (!donor) return;
    const amt = Math.min(shortM.shortageKg, donor.excessKg);
    if (amt <= 0) return;
    suggestions.push(
      `Reallocate ${amt.toLocaleString()} kg from ${donor.name} to ${shortM.name}`,
    );
    usedDonorIds.add(donor.id);
  });

  if (suggestions.length === 0 && shortRows.length > 0) {
    const assignedFarms = new Set();
    rawRoutes.forEach((r) => {
      (r.stops || []).forEach((s) => {
        if (!s.demand_point_id && s.label) assignedFarms.add(s.label);
      });
    });

    const farms = Array.isArray(cached?.farms) && cached.farms.length ? cached.farms : DEMO_FARMS;
    for (const shortM of shortRows) {
      if (suggestions.length >= 5) break;
      const farm = farms.find((f) => {
        if (assignedFarms.has(f.id)) return false;
        const kg = atRiskMap[f.id]?.kg_at_risk ?? 0;
        return kg > 0;
      });
      if (!farm) continue;
      const kg = atRiskMap[farm.id]?.kg_at_risk ?? 0;
      const amt = Math.min(shortM.shortageKg, Math.round(kg));
      if (amt <= 0) continue;
      suggestions.push(
        `Assign ${amt.toLocaleString()} kg from ${farm.name || farm.id} to ${shortM.name}`,
      );
      assignedFarms.add(farm.id);
    }
  }

  if (suggestions.length === 0 && shortRows.length > 0) {
    return ['No reallocation possible with current plan'];
  }

  return suggestions;
}

