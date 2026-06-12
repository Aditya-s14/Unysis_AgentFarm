import { displayTruckId } from '@/utils/truckDisplay';

/**
 * Shows recent route deviation alerts for the active run.
 */
export default function DeviationAlertPanel({ alerts }) {
  if (!alerts?.length) return null;

  const open = alerts.filter((a) => a.status === 'open');
  const recent = alerts.slice(0, 5);

  return (
    <div
      className="bg-card p-5 mb-6"
      style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
    >
      <p
        className="font-mono uppercase mb-3"
        style={{ color: 'var(--warn)', fontSize: '0.65rem', letterSpacing: '0.15em' }}
      >
        ▸ Route deviation alerts
        {open.length > 0 && (
          <span style={{ color: 'var(--danger)', marginLeft: '8px' }}>
            ({open.length} open)
          </span>
        )}
      </p>
      <ul className="space-y-3">
        {recent.map((alert) => (
          <li
            key={alert.alert_id}
            className="font-mono text-[12px] p-3"
            style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
          >
            <span className="font-syne font-bold text-paper">
              {displayTruckId(alert.truck_id)}
            </span>
            <span className="text-muted"> — </span>
            <span style={{ color: alert.status === 'open' ? 'var(--danger)' : 'var(--muted)' }}>
              {alert.deviation_km?.toFixed?.(1) ?? alert.deviation_km} km off route
            </span>
            {alert.notified_at && (
              <p className="text-muted text-[10px] mt-1 m-0">
                Notified {new Date(alert.notified_at).toLocaleTimeString()}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
