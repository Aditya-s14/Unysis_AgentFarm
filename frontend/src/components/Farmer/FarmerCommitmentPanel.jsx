import { useMemo, useState } from 'react';
import {
  DEMO_DEMAND_POINTS,
  DEMO_FARMS,
} from '@/utils/demoFixtures';
import {
  daysUntilHarvest,
  listEligibleFarms,
  nearestMandiId,
  nearestMandiLabel,
} from '@/utils/commitmentEligibility';
import useFarmerCommitments from '@/hooks/useFarmerCommitments';

function CommitmentRow({
  farm,
  demandPoints,
  isLocked,
  lockedTonnage,
  onLock,
  onUnlock,
}) {
  const [tonnage, setTonnage] = useState(
    String(lockedTonnage ?? farm.typical_yield_kg ?? 0),
  );
  const mandiLabel = nearestMandiLabel(farm, demandPoints);
  const mandiId = nearestMandiId(farm, demandPoints);
  const days = daysUntilHarvest(farm);

  return (
    <div
      className="flex flex-col sm:flex-row sm:items-center gap-3 py-3 px-4"
      style={{ borderTop: '1px solid var(--border)' }}
    >
      <div className="flex-1 min-w-0">
        <p className="font-syne font-bold text-paper truncate" style={{ fontSize: '13px' }}>
          {farm.name}
        </p>
        <p className="font-mono text-muted mt-0.5" style={{ fontSize: '10px' }}>
          {farm.crop_type}
          {' · '}
          harvest in {days}d
          {' · '}
          → {mandiLabel}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <input
          type="number"
          min="0"
          step="50"
          value={tonnage}
          disabled={isLocked}
          onChange={(e) => setTonnage(e.target.value)}
          className="font-mono w-24 px-2 py-1.5"
          style={{
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: '2px',
            color: 'var(--text)',
            fontSize: '11px',
          }}
          aria-label={`Tonnage kg for ${farm.name}`}
        />
        <span className="font-mono text-muted" style={{ fontSize: '10px' }}>kg</span>
        {isLocked ? (
          <button
            type="button"
            onClick={() => onUnlock(farm.id)}
            className="font-mono uppercase tracking-wider px-3 py-1.5"
            style={{
              fontSize: '9px',
              border: '1px solid var(--green-ok)',
              color: 'var(--green-ok)',
              borderRadius: '2px',
              background: 'rgba(76, 175, 80, 0.08)',
            }}
          >
            Locked
          </button>
        ) : (
          <button
            type="button"
            onClick={() => onLock(farm.id, Number(tonnage), mandiId)}
            className="font-mono uppercase tracking-wider px-3 py-1.5"
            style={{
              fontSize: '9px',
              border: '1px solid var(--accent)',
              color: 'var(--accent)',
              borderRadius: '2px',
              background: 'rgba(245, 166, 35, 0.06)',
            }}
          >
            Lock
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Pre-commitment contracts — lock tonnage before running the scenario.
 */
export default function FarmerCommitmentPanel() {
  const {
    lockCommitment,
    unlockCommitment,
    isLocked,
    getCommitment,
    summary,
  } = useFarmerCommitments();

  const eligible = useMemo(
    () => listEligibleFarms(DEMO_FARMS),
    [],
  );
  const { count, totalKg } = summary();

  const handleLock = (farmId, tonnageKg, mandiId) => {
    if (!Number.isFinite(tonnageKg) || tonnageKg <= 0) return;
    lockCommitment(farmId, {
      tonnage_kg: tonnageKg,
      demand_point_id: mandiId,
    });
  };

  return (
    <section
      className="mb-6 p-5 md:p-6"
      style={{
        border: '1px solid var(--border)',
        borderRadius: '4px',
        background: 'var(--bg-card)',
      }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div>
          <p
            className="font-mono uppercase text-accent mb-1"
            style={{ fontSize: '0.65rem', letterSpacing: '0.15em' }}
          >
            ▸ Pre-Commitment Contracts
          </p>
          <p className="font-mono text-muted" style={{ fontSize: '11px', lineHeight: 1.5 }}>
            Lock crop tonnage up to 7 days before harvest. Committed supply gets full weight (1.0)
            vs forecast (0.6) in the demand agent.
          </p>
        </div>
        <span
          className="font-mono uppercase shrink-0 px-3 py-1"
          style={{
            fontSize: '9px',
            letterSpacing: '0.12em',
            border: '1px solid var(--border)',
            borderRadius: '2px',
            color: count > 0 ? 'var(--green-ok)' : 'var(--muted)',
          }}
        >
          {count} committed · {totalKg.toLocaleString()} kg
        </span>
      </div>

      {eligible.length === 0 ? (
        <p className="font-mono text-muted px-4 py-3" style={{ fontSize: '11px' }}>
          No farms with harvest starting within 7 days. Check seed harvest windows.
        </p>
      ) : (
        <div style={{ borderBottom: '1px solid var(--border)' }}>
          <p
            className="font-mono text-muted px-4 py-2"
            style={{ fontSize: '10px', letterSpacing: '0.1em' }}
          >
            {eligible.length} ELIGIBLE / {DEMO_FARMS.length} FARMS
          </p>
          {eligible.map((farm) => (
            <CommitmentRow
              key={farm.id}
              farm={farm}
              demandPoints={DEMO_DEMAND_POINTS}
              isLocked={isLocked(farm.id)}
              lockedTonnage={getCommitment(farm.id)?.tonnage_kg}
              onLock={handleLock}
              onUnlock={unlockCommitment}
            />
          ))}
        </div>
      )}
    </section>
  );
}
