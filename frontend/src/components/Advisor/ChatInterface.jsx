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
    <div className="flex flex-col bg-white rounded-lg border border-gray-200 shadow-sm h-[70vh]">
      <div className="px-5 py-3 border-b border-gray-200">
        <h3 className="font-semibold text-agri-green-dark">Farmer Advisor</h3>
        <p className="text-xs text-gray-500">
          Session {sessionId?.slice(0, 8) || '...'} • Run {currentRunId || 'none'}
        </p>
      </div>

      <div ref={scrollerRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {messages.length === 0 ? (
          <div className="text-sm text-gray-500 italic">
            Ask the advisor a question. Examples below.
          </div>
        ) : (
          messages.map((m, idx) => (
            <ChatMessage key={idx} role={m.role} content={m.content} error={m.error} />
          ))
        )}
        {loading && (
          <div className="text-xs text-gray-400 italic">Advisor is thinking...</div>
        )}
        {error && !messages.some((m) => m.error) && (
          <div className="text-xs text-red-600">{error}</div>
        )}
      </div>

      <div className="px-5 py-2 border-t border-gray-100 flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => handleSend(s)}
            className="text-xs px-3 py-1 rounded-full border border-agri-green text-agri-green hover:bg-agri-green-light/30 transition"
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
        className="p-3 border-t border-gray-200 flex gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a farm, route, or mandi..."
          className="flex-1 px-3 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-agri-green"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 rounded-md bg-agri-green text-white text-sm font-medium hover:bg-agri-green-dark disabled:opacity-60"
        >
          Send
        </button>
      </form>
    </div>
  );
}
