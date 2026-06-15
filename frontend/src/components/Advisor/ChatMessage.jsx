/**
 * ChatMessage — single bubble in the Advisor chat.
 * User messages align right (saffron); assistant messages align left (card bg).
 * Errors get a risk-coloured border.
 */
export default function ChatMessage({ role, content, error }) {
  const isUser = role === 'user';

  const baseStyle = {
    maxWidth: '78%',
    padding: '10px 14px',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    fontFamily: "'IBM Plex Sans', sans-serif",
    fontSize: '13px',
    lineHeight: 1.55,
  };

  const userStyle = {
    ...baseStyle,
    background: 'var(--accent)',
    color: '#0D1F0F',
    borderRadius: '12px 12px 0 12px',
  };

  const assistantStyle = {
    ...baseStyle,
    background: 'var(--bg)',
    color: 'var(--text)',
    border: `1px solid ${error ? 'var(--red-risk)' : 'var(--border)'}`,
    borderRadius: '12px 12px 12px 0',
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div style={isUser ? userStyle : assistantStyle}>{content}</div>
    </div>
  );
}
