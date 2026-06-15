import { useState } from 'react';
import { reportBreakdown, replanBreakdown } from '@/api/client';
import { formatApiError } from '@/utils/api';

const REASONS = [
  { value: 'engine_failure', label: 'Engine failure' },
  { value: 'flat_tire', label: 'Flat tire' },
  { value: 'accident', label: 'Accident' },
  { value: 'fuel_empty', label: 'Fuel empty' },
  { value: 'other', label: 'Other' },
];

/**
 * Modal for reporting a truck breakdown.
 * - FPO default: report + partial re-plan
 * - Driver (reportOnly): submit incident only — FPO replans later
 * - FPO replan (replanIncidentId): replan a driver-reported incident
 */
export default function BreakdownReportModal({
  runId,
  truckId,
  farmStops,
  farmsById,
  onClose,
  onReported,
  reportOnly = false,
  replanIncidentId = null,
}) {
  const [reason, setReason] = useState('engine_failure');
  const [completedFarmIds, setCompletedFarmIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const isReplan = Boolean(replanIncidentId);
  const showFarmPickers = !reportOnly;

  const toggleFarm = (farmId) => {
    setCompletedFarmIds((prev) => (
      prev.includes(farmId)
        ? prev.filter((id) => id !== farmId)
        : [...prev, farmId]
    ));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!runId || !truckId) return;
    setLoading(true);
    setError(null);
    try {
      let preview;
      if (isReplan) {
        preview = await replanBreakdown(runId, replanIncidentId, {
          completed_farm_ids: completedFarmIds,
          spare_truck_id: null,
        });
      } else {
        preview = await reportBreakdown(runId, {
          truck_id: truckId,
          reported_by: reportOnly ? 'driver' : 'fpo',
          reason,
          completed_farm_ids: reportOnly ? [] : completedFarmIds,
          spare_truck_id: null,
          report_only: reportOnly,
        });
      }
      onReported?.(preview);
      onClose?.();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const submitLabel = reportOnly
    ? (loading ? 'Submitting…' : 'Submit report')
    : isReplan
      ? (loading ? 'Re-planning…' : 'Re-plan route')
      : (loading ? 'Re-planning…' : 'Report & re-plan');

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.65)' }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="breakdown-modal-title"
    >
      <div
        className="w-full max-w-md p-6 font-mono"
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: '4px',
        }}
      >
        <p
          id="breakdown-modal-title"
          className="font-syne font-bold uppercase text-paper mb-1"
          style={{ fontSize: '14px', letterSpacing: '0.06em' }}
        >
          {reportOnly ? 'Report breakdown' : isReplan ? 'Re-plan route' : 'Report breakdown'}
        </p>
        <p className="text-muted text-[12px] mb-4 leading-relaxed">
          {reportOnly ? (
            <>Truck {truckId} — describe what happened. Your FPO coordinator will re-plan the route.</>
          ) : isReplan ? (
            <>Truck {truckId} — mark farms already picked up, then re-plan remaining pickups onto a spare truck.</>
          ) : (
            <>Truck {truckId} — mark farms already picked up, then submit to re-plan remaining pickups onto a spare truck.</>
          )}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isReplan && (
            <label className="block">
              <span className="text-muted text-[10px] uppercase tracking-wider">Reason</span>
              <select
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="w-full mt-1 p-2 text-paper text-[12px]"
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: '2px',
                }}
              >
                {REASONS.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </label>
          )}

          {showFarmPickers && farmStops.length > 0 && (
            <fieldset>
              <legend className="text-muted text-[10px] uppercase tracking-wider mb-2">
                Farms already picked up (optional)
              </legend>
              <ul className="space-y-2 max-h-40 overflow-y-auto">
                {farmStops.map((stop) => {
                  const farm = farmsById?.get(stop.label);
                  const name = farm?.name || stop.label;
                  const checked = completedFarmIds.includes(stop.label);
                  return (
                    <li key={stop.label}>
                      <label className="flex items-center gap-2 text-[12px] cursor-pointer">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleFarm(stop.label)}
                        />
                        <span className="text-paper">{name}</span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            </fieldset>
          )}

          {error && (
            <p className="text-[12px]" style={{ color: 'var(--danger)' }}>{error}</p>
          )}

          <div className="flex gap-3 justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 uppercase text-[11px] tracking-wider"
              style={{
                border: '1px solid var(--border)',
                color: 'var(--muted)',
                borderRadius: '2px',
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 uppercase text-[11px] tracking-wider font-syne font-bold disabled:opacity-50"
              style={{
                background: reportOnly ? 'var(--accent)' : 'var(--danger)',
                color: reportOnly ? 'var(--accent-text)' : 'var(--bg-card)',
                borderRadius: '2px',
              }}
            >
              {submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
