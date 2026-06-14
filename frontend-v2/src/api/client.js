import axios from 'axios';
import { API_BASE_URL, formatApiError } from '@/utils/api';
import { clearToken, readToken } from '@/utils/auth';

/**
 * Shared axios instance for the AgentFarm backend.
 * All API calls must go through this module so interceptors / auth / errors
 * are handled uniformly.
 */
const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300_000, // 5 min — pipeline with 20 farms takes ~60-90s
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach the JWT to every request (T1).
client.interceptors.request.use((config) => {
  const token = readToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    // eslint-disable-next-line no-console
    console.error('[AgentFarm API]', formatApiError(error));
    // Expired/invalid session → back to login (skip auth endpoints, where
    // a 401 just means "wrong code", and skip when already on /login).
    const status = error?.response?.status;
    const url = error?.config?.url || '';
    if (
      status === 401 &&
      !url.includes('/auth/') &&
      typeof window !== 'undefined' &&
      !window.location.pathname.startsWith('/login')
    ) {
      clearToken();
      window.location.assign('/login');
    }
    return Promise.reject(error);
  },
);

/** POST /api/auth/request-otp — ask for a one-time code. */
export async function requestOtp(phone) {
  const { data } = await client.post('/auth/request-otp', { phone });
  return data;
}

/** POST /api/auth/verify-otp — exchange the code for a JWT. */
export async function verifyOtp(phone, code) {
  const { data } = await client.post('/auth/verify-otp', { phone, code });
  return data;
}

/** POST /api/scenario/run — kick off the full agent pipeline. */
export async function runScenario(body) {
  const { data } = await client.post('/scenario/run', body);
  return data;
}

/** GET /api/run/:id — fetch a finished plan + KPI summary. */
export async function getRun(runId) {
  const { data } = await client.get(`/run/${runId}`);
  return data;
}

/** POST /api/run/:id/approve — FPO sign-off; dispatch farmer + driver notifications. */
export async function approveRun(runId, body = {}) {
  const { data } = await client.post(`/run/${runId}/approve`, body);
  return data;
}

/** GET /api/run/:id/notifications — notification audit log. */
export async function getRunNotifications(runId) {
  const { data } = await client.get(`/run/${runId}/notifications`);
  return data;
}

/** POST /api/run/:id/breakdown — report truck breakdown and partial re-plan. */
export async function reportBreakdown(runId, body) {
  const { data } = await client.post(`/run/${runId}/breakdown`, body);
  return data;
}

/** POST /api/run/:id/breakdown/:incidentId/approve — approve delta notifications. */
export async function approveBreakdown(runId, incidentId) {
  const { data } = await client.post(`/run/${runId}/breakdown/${incidentId}/approve`);
  return data;
}

/** GET /api/run/:id/breakdown — list breakdown incidents. */
export async function getBreakdownIncidents(runId) {
  const { data } = await client.get(`/run/${runId}/breakdown`);
  return data;
}

/** POST /api/run/:id/tracking/:truckId/position — ingest driver GPS. */
export async function postTruckPosition(runId, truckId, body, headers = {}) {
  const { data } = await client.post(`/run/${runId}/tracking/${truckId}/position`, body, {
    headers,
  });
  return data;
}

/** GET /api/run/:id/tracking — live truck positions. */
export async function getTruckTracking(runId) {
  const { data } = await client.get(`/run/${runId}/tracking`);
  return data;
}

/** GET /api/run/:id/tracking/deviations — deviation alert history. */
export async function getDeviationAlerts(runId) {
  const { data } = await client.get(`/run/${runId}/tracking/deviations`);
  return data;
}

/** GET /api/run/:id/traces — fetch per-agent reasoning traces. */
export async function getRunTraces(runId) {
  const { data } = await client.get(`/run/${runId}/traces`);
  return data;
}

/** POST /api/advisor/query — ask the Advisor Agent a contextual question. */
export async function queryAdvisor({ runId, sessionId, userQuestion }) {
  const { data } = await client.post('/advisor/query', {
    run_id: runId,
    session_id: sessionId,
    question: userQuestion,
  });
  return data;
}

/** POST /api/outcome/log — log real-world outcomes to feed the learning loop. */
export async function logOutcome(outcomeBody) {
  const { data } = await client.post('/outcome/log', outcomeBody);
  return data;
}

/** POST /api/calendar/truck-gap — peak harvest fleet gap analysis + FPO alert. */
export async function checkTruckGap({ farms, trucks }) {
  const { data } = await client.post('/calendar/truck-gap', { farms, trucks });
  return data;
}

/** GET /api/analytics/season-trends — Tier-2 season-over-season metrics. */
export async function getSeasonTrends() {
  const { data } = await client.get('/analytics/season-trends');
  return data;
}

/** GET /api/price-board — APMC vs private buyer quotes. */
export async function getPriceBoard() {
  const { data } = await client.get('/price-board');
  return data;
}

/** POST /api/price-board/accept — farmer accepts private buyer offer. */
export async function acceptPrivateOffer(body) {
  const { data } = await client.post('/price-board/accept', body);
  return data;
}

/** GET /api/buyer/demand — list direct buyer demand posts. */
export async function getBuyerDemands() {
  const { data } = await client.get('/buyer/demand');
  return data;
}

/** POST /api/buyer/demand — create/update buyer demand post. */
export async function postBuyerDemand(body) {
  const { data } = await client.post('/buyer/demand', body);
  return data;
}

/** DELETE /api/buyer/demand/{postId} — remove buyer demand post. */
export async function deleteBuyerDemand(postId) {
  const { data } = await client.delete(`/buyer/demand/${postId}`);
  return data;
}

/** GET /api/market/offers — list bid/ask ledger offers. */
export async function getMarketOffers() {
  const { data } = await client.get('/market/offers');
  return data;
}

/** GET /api/market/accepted — list active market commitments. */
export async function getMarketAccepted() {
  const { data } = await client.get('/market/accepted');
  return data;
}

/** POST /api/market/offer — create bid or ask. */
export async function postMarketOffer(body) {
  const { data } = await client.post('/market/offer', body);
  return data;
}

/** POST /api/market/accept — accept open offer → guaranteed commitment. */
export async function acceptMarketOffer(body) {
  const { data } = await client.post('/market/accept', body);
  return data;
}

/** POST /api/economics/farm-margins — per-farm P&L after scenario run. */
export async function getFarmMargins(body) {
  const { data } = await client.post('/economics/farm-margins', body);
  return data;
}

/** GET /api/farmer/:farmId/ready — get crop-ready state from Redis. */
export async function getFarmerReady(farmId) {
  const { data } = await client.get(`/farmer/${farmId}/ready`);
  return data;
}

/** PATCH /api/farmer/:farmId/ready — set crop-ready state (24h TTL in Redis). */
export async function patchFarmerReady(farmId, ready) {
  const { data } = await client.patch(`/farmer/${farmId}/ready`, { ready });
  return data;
}

/** POST /api/run/:runId/farm/:farmId/arrival — farmer confirms truck arrival. */
export async function postFarmArrival(runId, farmId) {
  const { data } = await client.post(`/run/${runId}/farm/${farmId}/arrival`);
  return data;
}

/** POST /api/run/:runId/mandi/:mandiId/confirm — mandi confirms delivery arrival, writes to plan_outcomes. */
export async function postMandiConfirm(runId, mandiId, body) {
  const { data } = await client.post(`/run/${runId}/mandi/${mandiId}/confirm`, body);
  return data;
}

export default client;
