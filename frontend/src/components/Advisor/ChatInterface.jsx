import { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import useAdvisor from '@/hooks/useAdvisor';
import { useAppContext } from '@/context/AppContext';

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
  const { currentRunId, sessionId } = useAppContext();
  const { messages, loading, error, ask } = useAdvisor({
    runId: currentRunId,
    sessionId,
  });
  const [input, setInput] = useState('');
  const scrollerRef = useRef(null);

  useEffect(() => {
    scrollerRef.current?.scrollTo({
      top: scrollerRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages]);

  const handleSend = async (text) => {
    const q = (text ?? input).trim();
    if (!q) return;
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
          SESSION {sessionId?.slice(0, 8) || '…'} · RUN {currentRunId?.slice(0, 8) || 'NONE'}
        </p>
      </div>

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
          disabled={loading}
          className="px-5 py-2 font-mono uppercase tracking-wider-2 transition disabled:opacity-50"
          style={{
            background: 'var(--accent)',
            color: '#0D1F0F',
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
