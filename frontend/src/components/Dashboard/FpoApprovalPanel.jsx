import { useState } from 'react';
import { approveRun } from '@/api/client';
import { formatApiError } from '@/utils/api';

/**
 * FPO approval gateway — hold SMS/voice until the officer signs off the plan.
 */
export default function FpoApprovalPanel({ runId, approvalStatus, humanReview, onApproved }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState(approvalStatus || 'pending');

  if (!runId) return null;

  const dispatched = status === 'dispatched' || Boolean(result?.notifications_dispatched_at);

  const handleApprove = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await approveRun(runId);
      setResult(resp);
      setStatus(resp.approval_status || 'dispatched');
      onApproved?.(resp);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="bg-card p-5 mb-6"
      style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p
            className="font-mono uppercase mb-2"
            style={{ color: 'var(--accent)', fontSize: '0.65rem', letterSpacing: '0.15em' }}
          >
            ▸ FPO Approval Gateway
          </p>
          <p className="font-mono text-paper text-[13px] leading-relaxed max-w-2xl">
            Review routes on the dashboard tabs. When the plan looks good, approve to send
            pickup alerts to farmers and route assignments to truck drivers (mock SMS in logs).
          </p>
          {humanReview && !dispatched && (
            <p className="font-mono text-[12px] mt-2" style={{ color: 'var(--warn)' }}>
              This run flagged human review — you can still approve if the plan is acceptable.
            </p>
          )}
        </div>
        <div className="text-right shrink-0">
          <p className="font-mono text-muted text-[11px] mb-2 uppercase tracking-wider">
            Status:{' '}
            <span style={{ color: dispatched ? 'var(--green-ok)' : 'var(--accent)' }}>
              {dispatched ? 'NOTIFIED' : status.toUpperCase()}
            </span>
          </p>
          {!dispatched && (
            <button
              type="button"
              onClick={handleApprove}
              disabled={loading}
              className="font-syne font-bold uppercase tracking-wider px-5 py-2.5 transition-opacity disabled:opacity-50"
              style={{
                background: 'var(--accent)',
                color: 'var(--bg)',
                fontSize: '12px',
                borderRadius: '4px',
              }}
            >
              {loading ? 'Sending…' : 'Approve & Notify'}
            </button>
          )}
        </div>
      </div>
      {error && (
        <p className="font-mono text-[12px] mt-3" style={{ color: 'var(--danger)' }}>
          {error}
        </p>
      )}
      {result?.notifications && (
        <p className="font-mono text-[12px] mt-3" style={{ color: 'var(--green-ok)' }}>
          Sent {result.notifications.sent} notification(s)
          {result.notifications.failed ? ` (${result.notifications.failed} failed)` : ''}.
          Check backend logs for MOCK SMS / MOCK VOICE lines.
        </p>
      )}
    </div>
  );
}
