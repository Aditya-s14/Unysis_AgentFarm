import { useCallback, useState } from 'react';
import { queryAdvisor } from '@/api/client';
import { formatApiError } from '@/utils/api';

/**
 * Hook that wraps the Advisor Agent query endpoint and maintains a local
 * conversation buffer for rendering.
 * Real server-side memory lives in Redis (keyed by sessionId).
 */
export function useAdvisor({ runId, sessionId }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const ask = useCallback(
    async (userQuestion) => {
      if (!userQuestion || !userQuestion.trim()) return null;
      const userMsg = { role: 'user', content: userQuestion, ts: Date.now() };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);
      setError(null);
      try {
        const response = await queryAdvisor({ runId, sessionId, userQuestion });
        const assistantMsg = {
          role: 'assistant',
          content: response?.answer || '(no answer)',
          ts: Date.now(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
        return response;
      } catch (err) {
        const message = formatApiError(err);
        setError(message);
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: `Error: ${message}`, ts: Date.now(), error: true },
        ]);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [runId, sessionId],
  );

  const reset = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, loading, error, ask, reset };
}

export default useAdvisor;
