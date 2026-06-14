import { EM_DASH, WARN } from '@/utils/uiChars';

/**
 * Banner when peak harvest is within 14 days and registered fleet is insufficient.
 */
export default function TruckGapAlertPanel({ analysis }) {
  if (!analysis || !analysis.alert_due || !(analysis.truck_gap > 0)) {
    return null;
  }

  const {
    peak_date: peakDate,
    days_until_peak: daysUntil,
    registered_trucks: registered,
    trucks_needed: needed,
    truck_gap: gap,
    farms_on_peak: farmsOnPeak = [],
    crop_summary: cropSummary,
    alert_dispatched: alertDispatched,
  } = analysis;

  return (
    <div
      className="p-4 space-y-3"
      style={{
        border: '1px solid var(--red-risk)',
        borderTop: '3px solid var(--red-risk)',
        borderRadius: '4px',
        background: 'rgba(255, 68, 68, 0.06)',
      }}
    >
      <div className="flex items-start gap-2">
        <span aria-hidden style={{ fontSize: '18px', lineHeight: 1 }}>{WARN}</span>
        <div className="space-y-1">
          <p
            className="font-syne font-bold uppercase tracking-wider-2"
            style={{ fontSize: '13px', color: 'var(--red-risk)' }}
          >
            Peak harvest truck shortage
          </p>
          <p className="font-mono" style={{ fontSize: '12px', color: 'var(--text)', lineHeight: 1.55 }}>
            Peak harvest on{' '}
            <strong>{peakDate}</strong>
            {' '}
            ({daysUntil} day{daysUntil !== 1 ? 's' : ''} away).
            Registered fleet: {registered} trucks; estimated need: {needed} (gap {gap}).
          </p>
          {cropSummary && (
            <p className="font-mono text-muted" style={{ fontSize: '11px' }}>
              Crops: {cropSummary}
            </p>
          )}
        </div>
      </div>

      {farmsOnPeak.length > 0 && (
        <p className="font-mono text-muted" style={{ fontSize: '10px', lineHeight: 1.5 }}>
          Farms on peak ({farmsOnPeak.length}): {farmsOnPeak.join(', ')}
        </p>
      )}

      {alertDispatched && (
        <p
          className="font-mono uppercase tracking-wider-2"
          style={{ fontSize: '10px', color: 'var(--green-ok)', letterSpacing: '0.12em' }}
        >
          FPO SMS sent {EM_DASH} register additional fleet before peak
        </p>
      )}
    </div>
  );
}
