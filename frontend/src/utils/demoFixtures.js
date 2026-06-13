/**
 * Full Bengaluru-cluster + Maharashtra fixtures used by the demo scenario flow.
 * Matches the seed CSVs in data/: 20 farms, 10 demand points, 10 trucks.
 *
 * Farm:         { id, name, lat, lng, crop_type, acreage, typical_yield_kg,
 *                 harvest_window_start, harvest_window_end, phone, notify_opt_in, ... }
 * DemandPoint:  { id, name, lat, lng, point_type, base_demand_per_day }
 * Truck:        { id, capacity_kg, cost_per_km, availability_start, availability_end, driver_phone }
 */

/** Demo SMS numbers — farm-001 → +919900000001, tr-001 → +919910000001 */
function demoFarmPhone(id) {
  const n = parseInt(String(id).replace('farm-', ''), 10);
  return `+9199000${String(n).padStart(5, '0')}`;
}

function demoTruckPhone(id) {
  const n = parseInt(String(id).replace('tr-', ''), 10);
  return `+9199100${String(n).padStart(5, '0')}`;
}

function withFarmContacts(farm) {
  return {
    ...farm,
    phone: demoFarmPhone(farm.id),
    notify_opt_in: true,
    notify_channel: 'both',
    preferred_language: farm.id === 'farm-003' ? 'hi' : 'en',
  };
}

function withTruckContacts(truck) {
  return {
    ...truck,
    driver_phone: demoTruckPhone(truck.id),
  };
}

// ── 20 Farms ──────────────────────────────────────────────────────────────
const _RAW_FARMS = [
  // Karnataka — Tomatoes
  { id: 'farm-001', name: 'Nandi Valley Tomatoes',          lat: 13.0827, lng: 77.5439, crop_type: 'tomato', acreage:  8.4, typical_yield_kg: 1200, harvest_window_start: '2026-06-15', harvest_window_end: '2026-07-30' },
  { id: 'farm-002', name: 'Tumkur Organic Tomato Coop',     lat: 13.3409, lng: 77.1011, crop_type: 'tomato', acreage: 11.2, typical_yield_kg: 1800, harvest_window_start: '2026-06-12', harvest_window_end: '2026-07-25' },
  { id: 'farm-003', name: 'Raichur Table Tomato Estate',    lat: 16.2076, lng: 77.3463, crop_type: 'tomato', acreage:  6.8, typical_yield_kg: 4000, harvest_window_start: '2026-06-26', harvest_window_end: '2026-08-30' },
  { id: 'farm-004', name: 'Chikkaballapur Cherry Tomatoes', lat: 13.4322, lng: 77.7275, crop_type: 'tomato', acreage:  9.1, typical_yield_kg: 1500, harvest_window_start: '2026-06-18', harvest_window_end: '2026-08-01' },
  { id: 'farm-005', name: 'Bellary Tomato Farmers Union',   lat: 15.1394, lng: 76.9214, crop_type: 'tomato', acreage: 14.0, typical_yield_kg: 4000, harvest_window_start: '2026-06-26', harvest_window_end: '2026-08-30' },
  // Maharashtra — Onions
  { id: 'farm-006', name: 'Nasik Hills Onion Growers',      lat: 19.9975, lng: 73.7898, crop_type: 'onion',  acreage: 10.5, typical_yield_kg:  900, harvest_window_start: '2026-06-14', harvest_window_end: '2026-07-15' },
  { id: 'farm-007', name: 'Solapur Red Onion Collective',   lat: 17.6599, lng: 75.9064, crop_type: 'onion',  acreage: 18.3, typical_yield_kg: 4000, harvest_window_start: '2026-06-26', harvest_window_end: '2026-08-30' },
  { id: 'farm-008', name: 'Sangli Onion Cooperatives',      lat: 16.8524, lng: 74.5815, crop_type: 'onion',  acreage: 12.7, typical_yield_kg: 4000, harvest_window_start: '2026-06-26', harvest_window_end: '2026-08-30' },
  { id: 'farm-009', name: 'Dhule Onion Plains',             lat: 20.9042, lng: 74.7778, crop_type: 'onion',  acreage:  9.4, typical_yield_kg: 4000, harvest_window_start: '2026-06-26', harvest_window_end: '2026-08-30' },
  { id: 'farm-010', name: 'Pune Plateau Onions',            lat: 18.5204, lng: 73.8567, crop_type: 'onion',  acreage:  7.2, typical_yield_kg: 4000, harvest_window_start: '2026-06-26', harvest_window_end: '2026-08-30' },
  // Karnataka — Bananas
  { id: 'farm-011', name: 'Chikmagalur Robusta Banana',     lat: 13.3161, lng: 75.7720, crop_type: 'banana', acreage: 15.6, typical_yield_kg:  700, harvest_window_start: '2026-06-16', harvest_window_end: '2026-09-30' },
  { id: 'farm-012', name: 'Coastal Karwar Cavendish',       lat: 14.8136, lng: 74.1286, crop_type: 'banana', acreage: 22.1, typical_yield_kg: 4000, harvest_window_start: '2026-06-26', harvest_window_end: '2026-08-30' },
  { id: 'farm-013', name: 'Mysore Nendran Banana Trust',    lat: 12.2958, lng: 76.6394, crop_type: 'banana', acreage: 11.0, typical_yield_kg: 4000, harvest_window_start: '2026-06-26', harvest_window_end: '2026-08-30' },
  { id: 'farm-014', name: 'Shivamogga Hill Plantains',      lat: 13.9299, lng: 75.5681, crop_type: 'banana', acreage: 13.8, typical_yield_kg:  850, harvest_window_start: '2026-05-12', harvest_window_end: '2026-09-05' },
  { id: 'farm-015', name: 'Haveri Grand Naine',             lat: 14.8006, lng: 75.3910, crop_type: 'banana', acreage: 19.4, typical_yield_kg: 1000, harvest_window_start: '2026-04-28', harvest_window_end: '2026-08-28' },
  // Maharashtra — Mangoes
  { id: 'farm-016', name: 'Ratnagiri Alphonso Grove',       lat: 16.9902, lng: 73.3120, crop_type: 'mango',  acreage: 25.0, typical_yield_kg:  750, harvest_window_start: '2026-06-13', harvest_window_end: '2026-07-30' },
  { id: 'farm-017', name: 'Devgad Mango Estates',           lat: 16.3869, lng: 73.3984, crop_type: 'mango',  acreage: 30.5, typical_yield_kg:  900, harvest_window_start: '2026-06-19', harvest_window_end: '2026-08-15' },
  { id: 'farm-018', name: 'Belgaum Kesar Block',            lat: 15.8497, lng: 74.4977, crop_type: 'mango',  acreage: 18.2, typical_yield_kg:  500, harvest_window_start: '2026-03-25', harvest_window_end: '2026-06-20' },
  { id: 'farm-019', name: 'Dharwad Banganapalli Farms',     lat: 15.4589, lng: 75.0078, crop_type: 'mango',  acreage: 12.3, typical_yield_kg:  400, harvest_window_start: '2026-04-05', harvest_window_end: '2026-06-25' },
  { id: 'farm-020', name: 'Bijapur Mango Collective',       lat: 16.8244, lng: 75.7154, crop_type: 'mango',  acreage: 21.7, typical_yield_kg:  650, harvest_window_start: '2026-03-30', harvest_window_end: '2026-07-10' },
];

export const DEMO_FARMS = _RAW_FARMS.map(withFarmContacts);

// ── 10 Demand Points ──────────────────────────────────────────────────────
export const DEMO_DEMAND_POINTS = [
  // APMC Yards
  { id: 'dp-apmc-01', name: 'Yeshwanthpur APMC Yard',        lat: 13.0280, lng: 77.5366, point_type: 'apmc',    base_demand_per_day: 2000 },
  { id: 'dp-apmc-02', name: 'Kolar Regional APMC',           lat: 13.1362, lng: 78.1295, point_type: 'apmc',    base_demand_per_day: 1400 },
  { id: 'dp-apmc-03', name: 'Hubli APMC Main Gate',          lat: 15.3647, lng: 75.1239, point_type: 'apmc',    base_demand_per_day: 1800 },
  { id: 'dp-apmc-04', name: 'Nashik Wholesale APMC',         lat: 19.9975, lng: 73.7898, point_type: 'apmc',    base_demand_per_day: 1900 },
  { id: 'dp-apmc-05', name: 'Solapur Tomato Auction APMC',   lat: 17.6599, lng: 75.9064, point_type: 'apmc',    base_demand_per_day: 1500 },
  { id: 'dp-apmc-06', name: 'Sangli Turmeric & Veg APMC',   lat: 16.8524, lng: 74.5815, point_type: 'apmc',    base_demand_per_day: 1300 },
  // Cover north-east Karnataka (Raichur/Bellary) and the Malnad belt
  // (Chikmagalur/Shivamogga) — without these, four demo farms sit >150 km
  // from every mandi and can never be routed (APMC radius constraint).
  { id: 'dp-apmc-07', name: 'Raichur APMC Yard',             lat: 16.2120, lng: 77.3439, point_type: 'apmc',    base_demand_per_day: 1200 },
  { id: 'dp-apmc-08', name: 'Davanagere APMC Market',        lat: 14.4644, lng: 75.9218, point_type: 'apmc',    base_demand_per_day: 1500 },
  // Private Distribution Centres
  { id: 'dp-priv-01', name: 'Reliance Fresh DC Pune',        lat: 18.5018, lng: 73.8745, point_type: 'private', base_demand_per_day: 1200 },
  { id: 'dp-priv-02', name: 'Metro Cash Nashik Ring Road',   lat: 19.9403, lng: 73.8341, point_type: 'private', base_demand_per_day: 1000 },
  { id: 'dp-priv-03', name: 'Star Bazaar Hubli Bypass',      lat: 15.4021, lng: 75.0777, point_type: 'private', base_demand_per_day:  800 },
  // Retail
  { id: 'dp-ret-01',  name: 'Mantri Square Retail Cluster',  lat: 12.9915, lng: 77.5696, point_type: 'retail',  base_demand_per_day:  500 },
];

// ── 10 Trucks (1-ton × 3, 3-ton × 4, 5-ton × 3) ─────────────────────────
const _RAW_TRUCKS = [
  { id: 'tr-001', capacity_kg: 1000, cost_per_km: 28.50, availability_start: '05:30:00', availability_end: '20:00:00' },
  { id: 'tr-002', capacity_kg: 1000, cost_per_km: 27.00, availability_start: '06:00:00', availability_end: '19:30:00' },
  { id: 'tr-003', capacity_kg: 1000, cost_per_km: 29.25, availability_start: '05:00:00', availability_end: '21:00:00' },
  { id: 'tr-004', capacity_kg: 3000, cost_per_km: 22.40, availability_start: '04:30:00', availability_end: '22:00:00' },
  { id: 'tr-005', capacity_kg: 3000, cost_per_km: 23.10, availability_start: '05:00:00', availability_end: '21:30:00' },
  { id: 'tr-006', capacity_kg: 3000, cost_per_km: 21.80, availability_start: '06:00:00', availability_end: '20:00:00' },
  { id: 'tr-007', capacity_kg: 3000, cost_per_km: 24.00, availability_start: '04:00:00', availability_end: '23:00:00' },
  { id: 'tr-008', capacity_kg: 5000, cost_per_km: 19.50, availability_start: '03:30:00', availability_end: '23:30:00' },
  { id: 'tr-009', capacity_kg: 5000, cost_per_km: 18.90, availability_start: '04:00:00', availability_end: '22:45:00' },
  { id: 'tr-010', capacity_kg: 5000, cost_per_km: 20.10, availability_start: '05:30:00', availability_end: '21:15:00' },
];

export const DEMO_TRUCKS = _RAW_TRUCKS.map(withTruckContacts);

/** D2 — seeded direct buyer demand posts (mirrors data/sample_buyer_demands.csv). */
export const DEMO_BUYER_DEMANDS = [
  {
    id: 'buyer-dp-priv-01-tomato',
    demand_point_id: 'dp-priv-01',
    buyer_name: 'Taj West End Kitchen',
    buyer_type: 'restaurant',
    crop_type: 'tomato',
    quantity_kg: 800,
    price_per_kg: 22,
  },
  {
    id: 'buyer-dp-priv-02-onion',
    demand_point_id: 'dp-priv-02',
    buyer_name: 'Metro Cash Nashik',
    buyer_type: 'supermarket',
    crop_type: 'onion',
    quantity_kg: 600,
    price_per_kg: 16,
  },
  {
    id: 'buyer-dp-priv-03-banana',
    demand_point_id: 'dp-priv-03',
    buyer_name: 'Export Hub Hubli',
    buyer_type: 'exporter',
    crop_type: 'banana',
    quantity_kg: 500,
    price_per_kg: 25,
  },
];

/** D4 — seeded market offers (mirrors data/sample_market_offers.csv). */
export const DEMO_MARKET_OFFERS = {
  offers: [
    {
      id: 'market-ask-dp-priv-01-tomato-seed001',
      side: 'ask',
      role: 'farmer',
      farm_id: 'farm-001',
      buyer_name: null,
      demand_point_id: 'dp-priv-01',
      crop_type: 'tomato',
      quantity_kg: 800,
      price_per_kg: 22,
      status: 'accepted',
    },
    {
      id: 'market-ask-dp-priv-02-onion-seed002',
      side: 'ask',
      role: 'farmer',
      farm_id: 'farm-006',
      buyer_name: null,
      demand_point_id: 'dp-priv-02',
      crop_type: 'onion',
      quantity_kg: 600,
      price_per_kg: 18,
      status: 'open',
    },
    {
      id: 'market-bid-dp-priv-03-banana-seed003',
      side: 'bid',
      role: 'buyer',
      farm_id: null,
      buyer_name: 'Export Hub Hubli',
      demand_point_id: 'dp-priv-03',
      crop_type: 'banana',
      quantity_kg: 500,
      price_per_kg: 25,
      status: 'open',
    },
    {
      id: 'market-bid-dp-priv-01-tomato-seed004',
      side: 'bid',
      role: 'buyer',
      farm_id: null,
      buyer_name: 'Taj West End Kitchen',
      demand_point_id: 'dp-priv-01',
      crop_type: 'tomato',
      quantity_kg: 750,
      price_per_kg: 23,
      status: 'open',
    },
  ],
  commitments: [
    {
      offer_id: 'market-ask-dp-priv-01-tomato-seed001',
      farm_id: 'farm-001',
      demand_point_id: 'dp-priv-01',
      crop_type: 'tomato',
      quantity_kg: 800,
      price_per_kg: 22,
      accepted_at: new Date().toISOString(),
    },
  ],
};

/** Undersized fleet to trigger validator capacity retries (demo / QA). */
export const DEMO_TRUCKS_CAPACITY_STRESS = DEMO_TRUCKS.slice(0, 3).map((t) => ({
  ...t,
  capacity_kg: 400,
}));

// ── MapView adapters ──────────────────────────────────────────────────────

/** Adapt an API-shaped farm to the {location:{lat,lng}} shape FarmMarker expects. */
export function toMapFarm(f) {
  return {
    id: f.id,
    name: f.name,
    crop_type: f.crop_type,
    acreage: f.acreage,
    location: { lat: f.lat, lng: f.lng },
  };
}

/** Adapt an API-shaped demand point to the {location:{lat,lng}} shape MandiMarker expects. */
export function toMapMandi(d) {
  return {
    id: d.id,
    name: d.name,
    type: d.point_type || d.type,
    base_demand_per_day: d.base_demand_per_day,
    location: { lat: d.lat, lng: d.lng },
  };
}

/** Pre-shaped arrays for direct use in MapView. */
export const DEMO_MAP_FARMS  = DEMO_FARMS.map(toMapFarm);
export const DEMO_MAP_MANDIS = DEMO_DEMAND_POINTS.map(toMapMandi);
