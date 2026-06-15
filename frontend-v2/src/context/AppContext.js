import { createContext, useContext, useMemo, useState, useCallback, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { clearToken, getStoredUser, saveToken } from '@/utils/auth';

/**
 * Application-wide state: current run id, advisor session id, and a draft
 * of the scenario the user is currently assembling.
 *
 * Persistence model:
 *   - `currentRunId`  → localStorage["agentfarm_run_id"]
 *   - `sessionId`     → localStorage["advisor_session_id"]
 *   - the full last response (with kpis, plan, traces) is also cached
 *     by the ScenarioForm under "agentfarm_last_response".
 *
 * Persisting in localStorage keeps these values stable across page
 * navigations (Next router) and full browser reloads.
 */
const AppContext = createContext(null);

const RUN_ID_KEY = 'agentfarm_run_id';
const SESSION_ID_KEY = 'advisor_session_id';

function safeRead(key) {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeWrite(key, value) {
  if (typeof window === 'undefined') return;
  try {
    if (value === null || value === undefined) {
      window.localStorage.removeItem(key);
    } else {
      window.localStorage.setItem(key, value);
    }
  } catch {
    /* localStorage disabled / quota exceeded */
  }
}

export function AppContextProvider({ children }) {
  const [currentRunId, setCurrentRunIdState] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [user, setUser] = useState(null);
  const [scenarioDraft, setScenarioDraft] = useState({
    scenarioType: 'monsoon_disruption',
    farms: [],
    demandPoints: [],
    trucks: [],
    constraints: {},
  });

  // Hydrate from localStorage on mount (client-only).
  useEffect(() => {
    const storedRunId = safeRead(RUN_ID_KEY);
    if (storedRunId) setCurrentRunIdState(storedRunId);

    let storedSession = safeRead(SESSION_ID_KEY);
    if (!storedSession) {
      storedSession = uuidv4();
      safeWrite(SESSION_ID_KEY, storedSession);
    }
    setSessionId(storedSession);

    setUser(getStoredUser());
  }, []);

  const setCurrentRunId = useCallback((id) => {
    setCurrentRunIdState(id);
    safeWrite(RUN_ID_KEY, id);
  }, []);

  const resetSession = useCallback(() => {
    const next = uuidv4();
    safeWrite(SESSION_ID_KEY, next);
    setSessionId(next);
  }, []);

  // T1: persist the JWT and expose the decoded user app-wide.
  const login = useCallback((token, expiresInSeconds) => {
    saveToken(token, expiresInSeconds);
    setUser(getStoredUser());
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      currentRunId,
      setCurrentRunId,
      sessionId,
      resetSession,
      scenarioDraft,
      setScenarioDraft,
      user,
      login,
      logout,
    }),
    [currentRunId, setCurrentRunId, sessionId, resetSession, scenarioDraft, user, login, logout],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

/** Hook to access the app-wide context. Throws if used outside the provider. */
export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error('useAppContext must be used inside <AppContextProvider>');
  }
  return ctx;
}

export default AppContext;
