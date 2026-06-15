import { useEffect, useState } from 'react';
import { getFarmerReady, patchFarmerReady } from '@/api/client';

/**
 * CropReadyToggle — lets a farmer mark their crop as ready for pickup.
 * Reads from and writes to Redis via GET/PATCH /api/farmer/{farmId}/ready.
 */
export default function CropReadyToggle({ farmId }) {
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!farmId) return;
    setLoading(true);
    getFarmerReady(farmId)
      .then((d) => { setReady(d.ready); setError(null); })
      .catch(() => setError('Could not load crop status'))
      .finally(() => setLoading(false));
  }, [farmId]);

  const toggle = async () => {
    setSaving(true);
    setError(null);
    try {
      const d = await patchFarmerReady(farmId, !ready);
      setReady(d.ready);
    } catch {
      setError('Failed to update. Try again.');
    } finally {
      setSaving(false);
    }
  };

  const color = ready ? 'var(--green-ok)' : 'var(--muted)';
  const label = ready ? 'CROP READY' : 'NOT READY';

  return (
    <div
      className="p-5"
      style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg-card)' }}
    >
      <p className="font-mono uppercase text-[10px] tracking-widest mb-3" style={{ color: 'var(--muted)' }}>
        Crop Ready Status
      </p>

      {loading ? (
        <p className="font-mono text-muted text-[12px]">Loading…</p>
      ) : (
        <div className="flex items-center gap-4">
          <div
            className="w-4 h-4 rounded-full flex-shrink-0"
            style={{ background: color, boxShadow: ready ? `0 0 8px ${color}` : 'none' }}
          />
          <span className="font-syne font-bold" style={{ fontSize: '16px', color }}>
            {label}
          </span>
          <button
            type="button"
            onClick={toggle}
            disabled={saving}
            className="ml-auto px-4 py-2 font-mono uppercase tracking-wider transition-all"
            style={{
              fontSize: '11px',
              border: '1px solid var(--accent)',
              borderRadius: '2px',
              background: ready ? 'var(--orange-selected)' : 'transparent',
              color: 'var(--accent)',
              cursor: saving ? 'not-allowed' : 'pointer',
              opacity: saving ? 0.6 : 1,
            }}
          >
            {saving ? 'Saving…' : ready ? 'Mark Not Ready' : 'Mark Ready'}
          </button>
        </div>
      )}

      {error && (
        <p className="font-mono mt-2 text-[11px]" style={{ color: 'var(--danger)' }}>{error}</p>
      )}

      <p className="font-mono mt-3 text-[11px]" style={{ color: 'var(--muted)' }}>
        Status resets automatically after 24 hours.
      </p>
    </div>
  );
}
