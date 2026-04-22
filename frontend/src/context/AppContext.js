import { createContext, useContext, useMemo, useState, useCallback, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';

/**
 * Application-wide state: current run id, advisor session id, and a draft
 * of the scenario the user is currently assembling.
 *
 * This is intentionally small — larger pieces of server state live in
 * react hooks (see src/hooks) and are not cached here.
 */
const AppContext = createContext(null);

export function AppContextProvider({ children }) {
  const [currentRunId, setCurrentRunId] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [scenarioDraft, setScenarioDraft] = useState({
    scenarioType: 'monsoon_disruption',
    farms: [],
    demandPoints: [],
    trucks: [],
    constraints: {},
  });

  // Generate a session id once on the client side (keeps SSR stable).
  useEffect(() => {
    if (!sessionId) {
      setSessionId(uuidv4());
    }
  }, [sessionId]);

  const resetSession = useCallback(() => {
    setSessionId(uuidv4());
  }, []);

  const value = useMemo(
    () => ({
      currentRunId,
      setCurrentRunId,
      sessionId,
      resetSession,
      scenarioDraft,
      setScenarioDraft,
    }),
    [currentRunId, sessionId, resetSession, scenarioDraft],
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
