import { useState } from 'react';

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

export default function MandiFulfilmentCard({
  row,
  isFirst,
  canLogOutcome,
  isLogged,
  onConfirmDelivery,
}) {
  const [open, setOpen] = useState(false);
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
        e.currentTarget.style.background = 'rgba(245, 166, 35, 0.03)';
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
          {isLogged && (
            <span
              className="font-mono uppercase inline-flex items-center gap-1.5"
              style={{
                fontSize: '9px',
                letterSpacing: '0.14em',
                padding: '4px 10px',
                borderRadius: '2px',
                border: '1px solid var(--green-ok)',
                color: 'var(--green-ok)',
                background: 'rgba(76, 175, 80, 0.08)',
              }}
            >
              LOGGED
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
              background: 'rgba(255,255,255,0.03)',
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
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
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
          label="Total available"
          value={`${row.totalAvailable.toLocaleString()} kg`}
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

      {canLogOutcome && row.incomingSupply > 0 && !isLogged && onConfirmDelivery && (
        <button
          type="button"
          onClick={() => onConfirmDelivery(row)}
          className="mb-4 font-mono uppercase tracking-wider w-full py-2"
          style={{
            fontSize: '10px',
            letterSpacing: '0.12em',
            border: '1px solid var(--accent)',
            color: 'var(--accent)',
            borderRadius: '2px',
            background: 'rgba(245, 166, 35, 0.06)',
          }}
        >
          Confirm delivery
        </button>
      )}

      {/* Details expander */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="font-mono uppercase tracking-wider"
        style={{
          fontSize: '9px',
          letterSpacing: '0.16em',
          color: 'var(--accent)',
          padding: '4px 0',
        }}
        aria-expanded={open}
      >
        {open ? '▾' : '▸'} Show details
      </button>

      {open && (
        <div
          className="mt-4 pt-4 space-y-4"
          style={{ borderTop: '1px solid var(--border)' }}
        >
          <div className="grid grid-cols-2 gap-4">
            <CoreMetric
              label="Current stock"
              value={`${row.currentStock.toLocaleString()} kg`}
            />
            <CoreMetric
              label="Usable stock"
              value={`${row.usableStock.toLocaleString()} kg`}
            />
          </div>

          {row.incomingTrucks.length > 0 ? (
            <div>
              <p
                className="font-mono text-muted uppercase mb-2"
                style={{ fontSize: '9px', letterSpacing: '0.14em' }}
              >
                Incoming trucks
              </p>
              <ul className="space-y-1.5">
                {row.incomingTrucks.map((t, i) => (
                  <li
                    key={`${t.truck_id}-${i}`}
                    className="font-mono flex justify-between gap-2"
                    style={{ fontSize: '11px', color: 'var(--text)' }}
                  >
                    <span>{t.truck_id}</span>
                    <span className="text-muted">{t.load_kg.toLocaleString()} kg</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="font-mono text-muted" style={{ fontSize: '11px' }}>
              No trucks assigned to this mandi in the current plan.
            </p>
          )}
        </div>
      )}
    </article>
  );
}
