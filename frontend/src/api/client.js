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

export default client;
