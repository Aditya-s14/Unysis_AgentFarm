import { displayTruckId } from '@/utils/truckDisplay';

const STATUS_SHORT = {
  'CRITICAL SHORTAGE': 'CRITICAL',
  SHORTAGE: 'SHORTAGE',
  'NEARLY MET': 'NEARLY MET',
  'SUPPLY MET': 'SUPPLY MET',
  EXCESS: 'EXCESS',
};

function CoreMetric({ label, value, accent }) {
  return (
    <div>
      <p
        className="font-mono text-muted uppercase"
        style={{ fontSize: '9px', letterSpacing: '0.12em' }}
      >
        {label}
      </p>
      <p
        className="font-syne font-bold mt-1"
        style={{ fontSize: '15px', color: accent || 'var(--text)' }}
      >
        {value}
      </p>
    </div>
  );
}

function IncomingTrucksList({
  trucks,
  canLogOutcome,
  mandiId,
  isTruckLogged,
  onConfirmDelivery,
  row,
}) {
  if (!trucks.length) {
    return (
      <p className="font-mono text-muted" style={{ fontSize: '11px' }}>
        No trucks assigned to this mandi in the current plan.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {trucks.map((t, i) => {
        const logged = isTruckLogged?.(mandiId, t.truck_id);
        const canConfirm = canLogOutcome && (t.load_kg ?? 0) > 0 && !logged && onConfirmDelivery;

        return (
          <li
            key={`${t.truck_id}-${i}`}
            className="flex items-center justify-between gap-3 py-2 px-3"
            style={{
              border: '1px solid var(--border)',
              borderRadius: '4px',
              background: logged ? 'var(--green-muted)' : 'var(--bg-subtle)',
            }}
          >
            <div className="min-w-0">
              <p className="font-syne font-bold text-[12px]" style={{ color: 'var(--navy)' }}>
                {displayTruckId(t.truck_id)}
              </p>
              <p className="font-mono text-muted mt-0.5" style={{ fontSize: '11px' }}>
                {t.load_kg.toLocaleString()} kg
              </p>
            </div>
            {logged ? (
              <span
                className="font-mono uppercase shrink-0"
                style={{
                  fontSize: '9px',
                  letterSpacing: '0.1em',
                  color: 'var(--green-ok)',
                  border: '1px solid var(--green-ok)',
                  borderRadius: '2px',
                  padding: '4px 8px',
                }}
              >
                Confirmed
              </span>
            ) : canConfirm ? (
              <button
                type="button"
                onClick={() => onConfirmDelivery(row, t)}
                className="font-mono uppercase tracking-wider shrink-0 py-1.5 px-3"
                style={{
                  fontSize: '9px',
                  letterSpacing: '0.1em',
                  border: '1px solid var(--accent)',
                  color: 'var(--accent)',
                  borderRadius: '2px',
                  background: 'var(--accent-muted)',
                }}
              >
                Confirm
              </button>
            ) : (
              <span className="font-mono text-muted shrink-0" style={{ fontSize: '10px' }}>
                {(t.load_kg ?? 0) > 0 ? 'Pending' : 'No load'}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export default function MandiFulfilmentCard({
  row,
  isFirst,
  canLogOutcome,
  isLogged,
  isTruckLogged,
  onConfirmDelivery,
}) {
  const barWidth = Math.min(100, (row.fulfilmentPct / 200) * 100);
  const statusShort = STATUS_SHORT[row.statusLabel] || row.statusLabel;

  const gapLabel = row.shortageKg > 0
    ? `Shortage ${row.shortageKg.toLocaleString()} kg`
    : row.excessKg > 0
      ? `Excess ${row.excessKg.toLocaleString()} kg`
      : 'Balanced';

  const gapColor = row.shortageKg > 0
    ? 'var(--red-risk)'
    : row.excessKg > 0
      ? 'var(--green-ok)'
      : 'var(--muted)';

  const allTrucksLogged = isLogged?.(row.id, row.incomingTrucks);

  return (
    <article
      className="p-5 md:p-6"
      style={{
        borderTop: isFirst ? undefined : '1px solid var(--border)',
        borderLeft: '3px solid transparent',
        transition: 'border-color 0.2s ease, background 0.2s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderLeftColor = 'var(--accent)';
        e.currentTarget.style.background = 'var(--orange-selected)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderLeftColor = 'transparent';
        e.currentTarget.style.background = 'transparent';
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-5">
        <div className="min-w-0">
          <h4
            className="font-syne font-bold text-paper uppercase tracking-wide truncate"
            style={{ fontSize: '14px' }}
          >
            {row.name}
          </h4>
        </div>
        <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
          {allTrucksLogged && (
            <span
              className="font-mono uppercase inline-flex items-center gap-1.5"
              style={{
                fontSize: '9px',
                letterSpacing: '0.14em',
                padding: '4px 10px',
                borderRadius: '2px',
                border: '1px solid var(--green-ok)',
                color: 'var(--green-ok)',
                background: 'var(--green-muted)',
              }}
            >
              ALL LOGGED
            </span>
          )}
          <span
            className="font-mono uppercase inline-flex items-center gap-1.5"
            style={{
              fontSize: '9px',
              letterSpacing: '0.14em',
              padding: '4px 10px',
              borderRadius: '2px',
              border: `1px solid ${row.statusColor}`,
              color: row.statusColor,
              background: 'var(--bg-subtle)',
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: row.statusColor,
                flexShrink: 0,
              }}
            />
            {statusShort}
          </span>
        </div>
      </div>

      {/* Core numbers */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-5">
        <CoreMetric
          label="Expected demand"
          value={`${row.expectedDemand.toLocaleString()} kg`}
        />
        <CoreMetric
          label="Incoming supply"
          value={`${row.incomingSupply.toLocaleString()} kg`}
          accent={row.incomingSupply > 0 ? 'var(--green-ok)' : undefined}
        />
        <CoreMetric
          label="Current stock"
          value={`${row.currentStock.toLocaleString()} kg`}
        />
        <CoreMetric
          label="Usable stock"
          value={`${row.usableStock.toLocaleString()} kg`}
        />
        <CoreMetric label="Gap" value={gapLabel} accent={gapColor} />
      </div>

      {/* Fulfilment bar */}
      <div className="mb-4">
        <div className="flex justify-between items-baseline mb-2">
          <span
            className="font-mono uppercase text-muted"
            style={{ fontSize: '9px', letterSpacing: '0.14em' }}
          >
            Fulfilment
          </span>
          <span
            className="font-syne font-bold"
            style={{ fontSize: '16px', color: row.barColor }}
          >
            {row.fulfilmentPct.toFixed(1)}%
          </span>
        </div>
        <div
          style={{
            height: '10px',
            background: 'var(--border)',
            borderRadius: '3px',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${barWidth}%`,
              height: '100%',
              background: row.barColor,
              transition: 'width 0.5s ease',
            }}
          />
        </div>
      </div>

      {row.incomingTrucks.length > 0 && (
        <div className="mb-4">
          <p
            className="font-mono text-muted uppercase mb-2"
            style={{ fontSize: '9px', letterSpacing: '0.14em' }}
          >
            Incoming trucks
          </p>
          <IncomingTrucksList
            trucks={row.incomingTrucks}
            canLogOutcome={canLogOutcome}
            mandiId={row.id}
            isTruckLogged={isTruckLogged}
            onConfirmDelivery={onConfirmDelivery}
            row={row}
          />
        </div>
      )}
    </article>
  );
}
