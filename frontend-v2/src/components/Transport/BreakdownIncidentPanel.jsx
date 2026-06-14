import { useState } from 'react';
import { approveBreakdown } from '@/api/client';
import { formatApiError } from '@/utils/api';
import { displayTruckId } from '@/utils/truckDisplay';

/**
 * Shows pending breakdown incidents and Approve Replan & Notify action.
 */
export default function BreakdownIncidentPanel({
  runId,
  incidents,
  onApproved,
}) {
  const [loadingId, setLoadingId] = useState(null);
  const [error, setError] = useState(null);

  if (!runId || !incidents?.length) return null;

  const pending = incidents.filter((i) => i.status === 'pending_approval');
  if (!pending.length) return null;

  const handleApprove = async (incidentId) => {
    setLoadingId(incidentId);
    setError(null);
    try {
      const preview = await approveBreakdown(runId, incidentId);
      onApproved?.(preview);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div
      className="bg-card p-5 mb-6"
      style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
    >
      <p
        className="font-mono uppercase mb-3"
        style={{ color: 'var(--danger)', fontSize: '0.65rem', letterSpacing: '0.15em' }}
      >
        ▸ Breakdown assistance
      </p>

      <ul className="space-y-4">
        {pending.map((inc) => (
          <li
            key={inc.incident_id}
            className="p-4"
            style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-syne font-bold text-paper text-[13px]">
                  {displayTruckId(inc.truck_id)} — {inc.reason?.replace(/_/g, ' ')}
                </p>
                <p className="font-mono text-muted text-[11px] mt-1">
                  Spare: {inc.spare_truck_id ? displayTruckId(inc.spare_truck_id) : '—'}
                  {' · '}
                  {inc.pending_farm_ids?.length || 0} farm(s) to reassign
                </p>
                {!inc.validation?.valid && (
                  <p className="font-mono text-[11px] mt-2" style={{ color: 'var(--warn)' }}>
                    Validator warnings — review before approving.
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => handleApprove(inc.incident_id)}
                disabled={loadingId === inc.incident_id}
                className="font-syne font-bold uppercase tracking-wider px-4 py-2 disabled:opacity-50 shrink-0"
                style={{
                  background: 'var(--accent)',
                  color: 'var(--bg)',
                  fontSize: '11px',
                  borderRadius: '4px',
                }}
              >
                {loadingId === inc.incident_id ? 'Sending…' : 'Approve replan & notify'}
              </button>
            </div>
          </li>
        ))}
      </ul>

      {error && (
        <p className="font-mono text-[12px] mt-3" style={{ color: 'var(--danger)' }}>
          {error}
        </p>
      )}
    </div>
  );
}
