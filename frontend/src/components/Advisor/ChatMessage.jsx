/**
 * ChatMessage — single bubble in the Advisor chat.
 * User messages align right, assistant messages align left.
 */
export default function ChatMessage({ role, content, error }) {
  const isUser = role === 'user';
  const base =
    'max-w-[75%] px-4 py-2 rounded-lg text-sm whitespace-pre-wrap break-words';
  const tone = isUser
    ? 'bg-agri-green text-white rounded-br-sm'
    : error
      ? 'bg-red-50 border border-red-200 text-red-700 rounded-bl-sm'
      : 'bg-gray-100 text-gray-900 rounded-bl-sm';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`${base} ${tone}`}>{content}</div>
    </div>
  );
}
