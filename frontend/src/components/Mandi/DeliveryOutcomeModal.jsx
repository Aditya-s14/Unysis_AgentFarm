import { useMemo, useState } from 'react';
import { buildMandiOutcomeDraft } from '@/utils/outcomePayload';
import { formatApiError } from '@/utils/api';

function ReadOnlyField({ label, value, unit }) {
  return (
    <div>
      <p
        className="font-mono text-muted uppercase"
        style={{ fontSize: '9px', letterSpacing: '0.12em' }}
      >
        {label}
      </p>
      <p className="font-syne font-bold mt-1 text-paper" style={{ fontSize: '14px' }}>
        {value}{unit ? ` ${unit}` : ''}
      </p>
    </div>
  );
}

function EditableField({ label, value, onChange, unit, step = '1', min = '0' }) {
  return (
    <label className="block">
      <span
        className="font-mono text-muted uppercase block mb-1"
        style={{ fontSize: '9px', letterSpacing: '0.12em' }}
      >
        {label}
      </span>
      <div className="flex items-center gap-2">
        <input
          type="number"
          value={value}
          min={min}
          step={step}
          onChange={(e) => onChange(e.target.value)}
          className="w-full font-mono px-3 py-2"
          style={{
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: '2px',
            color: 'var(--text)',
            fontSize: '12px',
          }}
        />
        {unit && (
          <span className="font-mono text-muted shrink-0" style={{ fontSize: '11px' }}>
            {unit}
          </span>
        )}
      </div>
    </label>
  );
}

/**
 * Confirm delivery with pre-filled actuals for Tier-2 outcome logging.
 */
export default function DeliveryOutcomeModal({
  mandiRow,
  cached,
  rawRoutes,
  farms,
  onClose,
  onSubmit,
  loading,
}) {
  const draft = useMemo(
    () => buildMandiOutcomeDraft({ cached, mandiRow, rawRoutes, farms }),
    [cached, mandiRow, rawRoutes, farms],
  );

  const [demandActual, setDemandActual] = useState(String(draft.demand_actual));
  const [wasteActual, setWasteActual] = useState(String(draft.waste_kg_actual));
  const [deliveryActual, setDeliveryActual] = useState(
    () => Number(draft.delivery_time_actual_hours).toFixed(2),
  );
  const [notes, setNotes] = useState(draft.notes || '');
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await onSubmit({
        demand_actual: Number(demandActual),
        waste_kg_actual: Number(wasteActual),
        delivery_time_actual_hours: Number(deliveryActual),
        notes: notes.trim() || draft.notes,
      });
      onClose?.();
    } catch (err) {
      setError(formatApiError(err));
    }
  };

  if (!mandiRow) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.65)' }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="delivery-outcome-title"
    >
      <div
        className="w-full max-w-lg p-6 font-mono max-h-[90vh] overflow-y-auto"
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: '4px',
        }}
      >
        <p
          id="delivery-outcome-title"
          className="font-syne font-bold uppercase text-paper mb-1"
          style={{ fontSize: '14px', letterSpacing: '0.06em' }}
        >
          Confirm delivery
        </p>
        <p className="text-muted mb-5" style={{ fontSize: '11px', lineHeight: 1.5 }}>
          Record actual kg delivered, waste, and delivery time for {mandiRow.name}. This feeds Tier-2
          demand bias correction on the next run.
        </p>

        <div className="grid grid-cols-2 gap-4 mb-5 p-4" style={{ background: 'var(--bg)', borderRadius: '2px' }}>
          <ReadOnlyField label="Predicted demand" value={draft.demand_predicted.toLocaleString()} unit="kg" />
          <ReadOnlyField label="Predicted waste" value={draft.waste_kg_predicted.toLocaleString()} unit="kg" />
          <ReadOnlyField
            label="Predicted delivery"
            value={draft.delivery_time_predicted_hours.toFixed(2)}
            unit="hrs"
          />
          <ReadOnlyField label="Crop / weekday" value={`${draft.crop_type} · ${draft.day_of_week}`} />
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <EditableField
            label="Actual demand delivered"
            value={demandActual}
            onChange={setDemandActual}
            unit="kg"
          />
          <EditableField
            label="Actual waste"
            value={wasteActual}
            onChange={setWasteActual}
            unit="kg"
          />
          <EditableField
            label="Actual delivery time"
            value={deliveryActual}
            onChange={setDeliveryActual}
            unit="hrs"
            step="0.01"
          />
          <label className="block">
            <span
              className="font-mono text-muted uppercase block mb-1"
              style={{ fontSize: '9px', letterSpacing: '0.12em' }}
            >
              Notes
            </span>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="w-full font-mono px-3 py-2"
              style={{
                background: 'var(--bg)',
                border: '1px solid var(--border)',
                borderRadius: '2px',
                color: 'var(--text)',
                fontSize: '12px',
                resize: 'vertical',
              }}
            />
          </label>

          {error && (
            <p className="text-[11px]" style={{ color: 'var(--danger)' }}>
              {error}
            </p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="flex-1 font-mono uppercase tracking-wider py-2"
              style={{
                fontSize: '10px',
                border: '1px solid var(--border)',
                color: 'var(--muted)',
                borderRadius: '2px',
                background: 'transparent',
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 font-mono uppercase tracking-wider py-2"
              style={{
                fontSize: '10px',
                border: '1px solid var(--accent)',
                color: 'var(--bg)',
                background: 'var(--accent)',
                borderRadius: '2px',
              }}
            >
              {loading ? 'Logging…' : 'Log outcome'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
