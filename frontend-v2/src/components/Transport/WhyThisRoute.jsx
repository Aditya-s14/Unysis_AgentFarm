import { useMemo, useState } from 'react';
import { buildRouteExplanation } from '@/utils/routeExplanation';

/**
 * Collapsible "WHY THIS ROUTE" block for Transport truck cards.
 */
export default function WhyThisRoute({ stops, atRiskMap, mandiById, farmsById }) {
  const [open, setOpen] = useState(false);

  const text = useMemo(
    () => buildRouteExplanation({ stops, atRiskMap, mandiById, farmsById }),
    [stops, atRiskMap, mandiById, farmsById],
  );

  return (
    <div
      className="mt-3"
      onClick={(e) => e.stopPropagation()}
      role="presentation"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left font-mono uppercase tracking-wider"
        style={{
          fontSize: '9px',
          letterSpacing: '0.18em',
          color: 'var(--accent)',
          padding: '4px 0',
        }}
        aria-expanded={open}
      >
        {open ? '▾' : '▸'} WHY THIS ROUTE
      </button>
      {open && (
        <div
          className="mt-2 px-3 py-2.5"
          style={{
            borderLeft: '3px solid var(--accent)',
            background: 'rgba(245, 166, 35, 0.04)',
            borderRadius: '0 2px 2px 0',
          }}
        >
          <p
            className="font-mono leading-relaxed"
            style={{ fontSize: '10.5px', color: 'var(--muted)', lineHeight: 1.65 }}
          >
            {text}
          </p>
        </div>
      )}
    </div>
  );
}
