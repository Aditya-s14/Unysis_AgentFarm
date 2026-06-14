import { useState } from 'react';
import { postFarmArrival } from '@/api/client';

/**
 * ArrivalConfirmButton — lets the farmer confirm that the assigned truck has arrived.
 * Calls POST /api/run/:runId/farm/:farmId/arrival and writes the event to plan_outcomes.
 */
export default function ArrivalConfirmButton({ runId, farmId }) {
  const [status, setStatus] = useState('idle'); // idle | loading | confirmed | error

  async function handleConfirm() {
    if (!runId) {
      setStatus('error');
      return;
    }
    setStatus('loading');
    try {
      await postFarmArrival(runId, farmId);
      setStatus('confirmed');
    } catch {
      setStatus('error');
    }
  }

  return (
    <div
      className="p-5"
      style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
    >
      <p className="font-mono uppercase text-[10px] tracking-widest mb-3" style={{ color: 'var(--muted)' }}>
        Truck Arrival
      </p>

      {status === 'confirmed' ? (
        <div className="flex items-center gap-3">
          <span style={{ fontSize: 22, color: '#16a34a' }}>✓</span>
          <div>
            <p className="font-syne font-bold text-[13px]" style={{ color: '#16a34a' }}>
              Arrival confirmed
            </p>
            <p className="font-mono text-[11px] mt-0.5" style={{ color: 'var(--muted)' }}>
              Logged for learning loop
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-[13px]" style={{ color: 'var(--text-secondary)' }}>
            Has the assigned truck arrived at your farm? Tap below to confirm delivery.
          </p>
          {!runId ? (
            <p className="font-mono text-[11px]" style={{ color: 'var(--muted)' }}>
              No active run — waiting for FPO to run a scenario.
            </p>
          ) : (
            <>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={status === 'loading'}
                className="btn-primary"
                style={{
                  opacity: status === 'loading' ? 0.6 : 1,
                  cursor: status === 'loading' ? 'not-allowed' : 'pointer',
                  fontSize: 13,
                  padding: '10px 20px',
                }}
              >
                {status === 'loading' ? 'Confirming…' : 'Confirm Truck Arrival'}
              </button>
              {status === 'error' && (
                <p className="font-mono text-[11px]" style={{ color: 'var(--red-risk)' }}>
                  Failed to confirm. Please try again.
                </p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
