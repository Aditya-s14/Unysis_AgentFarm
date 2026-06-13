/**
 * Quick check: each mock route gets a distinct explanation string.
 * Run: node scripts/verifyRouteExplanations.mjs
 */
import { buildRouteExplanation } from '../src/utils/routeExplanation.js';

const farmsById = new Map([
  ['farm-001', { id: 'farm-001', name: 'Nandi Valley' }],
  ['farm-002', { id: 'farm-002', name: 'Hosur Greens' }],
  ['farm-003', { id: 'farm-003', name: 'Devanahalli Plot' }],
]);

const mandiById = new Map([
  ['dp-apmc-01', { id: 'dp-apmc-01', name: 'Yeshwanthpur APMC', statusLabel: 'CRITICAL SHORTAGE', fulfilmentPct: 32 }],
  ['dp-apmc-02', { id: 'dp-apmc-02', name: 'KR Market', statusLabel: 'SUPPLY MET', fulfilmentPct: 105 }],
]);

const atRiskMap = {
  'farm-001': { hours_until_spoilage: 18, kg_at_risk: 400 },
  'farm-002': { hours_until_spoilage: 52, kg_at_risk: 600 },
  'farm-003': { hours_until_spoilage: 36, kg_at_risk: 300 },
};

const routes = [
  {
    truck_id: 'tr-001',
    stops: [
      { sequence: 0, label: 'farm-001', demand_point_id: null },
      { sequence: 1, label: 'farm-002', demand_point_id: null },
      { sequence: 2, demand_point_id: 'dp-apmc-01' },
    ],
  },
  {
    truck_id: 'tr-002',
    stops: [
      { sequence: 0, label: 'farm-003', demand_point_id: null },
      { sequence: 1, demand_point_id: 'dp-apmc-02' },
    ],
  },
  {
    truck_id: 'tr-003',
    stops: [{ sequence: 0, demand_point_id: 'dp-apmc-01' }],
  },
];

const texts = routes.map((r) => {
  const text = buildRouteExplanation({
    stops: r.stops,
    atRiskMap,
    mandiById,
    farmsById,
  });
  return { truck: r.truck_id, text };
});

const unique = new Set(texts.map((t) => t.text));
console.log(JSON.stringify(texts, null, 2));
console.log(`\n${texts.length} routes, ${unique.size} unique explanations`);
if (unique.size !== texts.length) {
  console.error('FAIL: duplicate explanations across trucks');
  process.exit(1);
}
console.log('OK: all explanations are unique');
