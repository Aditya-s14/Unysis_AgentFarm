import { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import useAdvisor from '@/hooks/useAdvisor';
import { useAppContext } from '@/context/AppContext';
import { getRun } from '@/api/client';

const LAST_RESPONSE_KEY = 'agentfarm_last_response';

const SUGGESTIONS = [
  'What should Farm #7 do tomorrow?',
  'Best route for monsoon?',
  'Which mandi has the highest demand this week?',
];

/**
 * ChatInterface — conversational UI for the Advisor Agent.
 * Uses the session id from AppContext so follow-up questions share memory.
 */
export default function ChatInterface() {
  const { currentRunId, setCurrentRunId, sessionId } = useAppContext();
  const [resolvedRunId, setResolvedRunId] = useState(currentRunId);
  const [runNotice, setRunNotice] = useState(null);
  const { messages, loading, error, ask } = useAdvisor({
    runId: resolvedRunId,
    sessionId,
  });
  const [input, setInput] = useState('');
  const scrollerRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function resolveRun() {
      if (!currentRunId) {
        setResolvedRunId(null);
        setRunNotice('No run selected — run a scenario first, then return here.');
        return;
      }

      try {
        await getRun(currentRunId);
        if (!cancelled) {
          setResolvedRunId(currentRunId);
          setRunNotice(null);
        }
        return;
      } catch {
        /* stale run id — try cached scenario response */
      }

      try {
        const raw = window.localStorage.getItem(LAST_RESPONSE_KEY);
        const cached = raw ? JSON.parse(raw) : null;
        const cachedRunId = cached?.run_id;
        if (cachedRunId && cachedRunId !== currentRunId) {
          await getRun(cachedRunId);
          if (!cancelled) {
            setCurrentRunId(cachedRunId);
            setResolvedRunId(cachedRunId);
            setRunNotice('Switched to your latest scenario run.');
            return;
          }
        }
        if (cachedRunId) {
          await getRun(cachedRunId);
          if (!cancelled) {
            setResolvedRunId(cachedRunId);
            setRunNotice(null);
            return;
          }
        }
      } catch {
        /* no valid cached run */
      }

      if (!cancelled) {
        setResolvedRunId(currentRunId);
        setRunNotice(
          'Plan data for this run was not found. Run a new scenario, or ask anyway — the advisor will use the latest plan if available.',
        );
      }
    }

    resolveRun();
    return () => {
      cancelled = true;
    };
  }, [currentRunId, setCurrentRunId]);

  useEffect(() => {
    scrollerRef.current?.scrollTo({
      top: scrollerRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages]);

  const handleSend = async (text) => {
    const q = (text ?? input).trim();
    if (!q || !resolvedRunId) return;
    setInput('');
    await ask(q);
  };

  return (
    <div
      className="flex flex-col bg-card h-[70vh]"
      style={{
        border: '1px solid var(--border)',
        borderRadius: '4px',
      }}
    >
      <div
        className="px-5 py-3 flex items-baseline justify-between flex-wrap gap-2"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <h3
          className="font-syne font-bold tracking-wider-2 uppercase"
          style={{ color: 'var(--accent)', fontSize: '15px' }}
        >
          🌾 KISAN MITRA
        </h3>
        <p className="font-mono text-muted text-[11px] tracking-wider">
          SESSION {sessionId?.slice(0, 8) || '…'} · RUN {resolvedRunId?.slice(0, 8) || 'NONE'}
        </p>
      </div>

      {runNotice && (
        <p
          className="px-5 py-2 font-mono text-[11px]"
          style={{
            color: 'var(--accent)',
            borderBottom: '1px solid var(--border)',
            background: 'var(--orange-selected)',
          }}
        >
          {runNotice}
        </p>
      )}

      <div
        ref={scrollerRef}
        className="flex-1 overflow-y-auto px-5 py-4 space-y-3"
        style={{ background: 'var(--bg)' }}
      >
        {messages.length === 0 ? (
          <div className="font-mono text-muted text-[12px] italic">
            Ask the advisor a question. Try a suggestion below.
          </div>
        ) : (
          messages.map((m, idx) => (
            <ChatMessage key={idx} role={m.role} content={m.content} error={m.error} />
          ))
        )}
        {loading && (
          <div className="font-mono text-muted text-[11px] italic">◦ Advisor is thinking…</div>
        )}
        {error && !messages.some((m) => m.error) && (
          <div className="font-mono text-[11px]" style={{ color: 'var(--red-risk)' }}>
            {error}
          </div>
        )}
      </div>

      <div
        className="px-5 py-3 flex flex-wrap gap-2"
        style={{
          borderTop: '1px solid var(--border)',
          background: 'var(--bg-card)',
        }}
      >
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => handleSend(s)}
            className="font-mono text-[11px] px-3 py-1.5 transition hover:text-accent hover:border-accent"
            style={{
              color: 'var(--muted)',
              border: '1px solid var(--border)',
              borderRadius: '2px',
              background: 'transparent',
            }}
          >
            {s}
          </button>
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="p-3 flex gap-2"
        style={{ borderTop: '1px solid var(--border)' }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a farm, route, or mandi…"
          className="flex-1 px-3 py-2 font-mono text-[13px] focus:outline-none transition"
          style={{
            background: 'var(--bg)',
            color: 'var(--text)',
            border: '1px solid var(--border)',
            borderRadius: '2px',
          }}
          onFocus={(e) => {
            e.target.style.borderColor = 'var(--accent)';
          }}
          onBlur={(e) => {
            e.target.style.borderColor = 'var(--border)';
          }}
        />
        <button
          type="submit"
          disabled={loading || !resolvedRunId}
          className="px-5 py-2 font-mono uppercase tracking-wider-2 transition disabled:opacity-50"
          style={{
            background: 'var(--accent)',
            color: 'var(--forest)',
            fontSize: '11px',
            fontWeight: 600,
            borderRadius: '2px',
            letterSpacing: '0.15em',
          }}
        >
          Send →
        </button>
      </form>
    </div>
  );
}
