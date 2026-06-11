import Link from 'next/link';
import { useState } from 'react';
import WhyThisRoute from '@/components/Transport/WhyThisRoute';
import { buildRouteLabel, displayTruckId, truncateRoute } from '@/utils/truckDisplay';

function MetricSkeleton({ width = '100px' }) {
  return (
    <span
      className="metric-skeleton font-mono"
      style={{ width }}
      aria-hidden
    />
  );
}

function RouteLine({ farmNames, dpNames }) {
  const [expanded, setExpanded] = useState(false);
  const full = buildRouteLabel(farmNames, dpNames);
  const { short, truncated } = truncateRoute(full);

  if (!full) {
    return (
      <p className="font-mono text-muted m-0" style={{ fontSize: '11px' }}>
        No stops on route
      </p>
    );
  }

  return (
    <div className="font-mono" style={{ fontSize: '11px', lineHeight: 1.6 }}>
      <span className="text-muted">Route: </span>
      <span style={{ color: 'var(--text)' }}>{expanded || !truncated ? full : short}</span>
      {truncated && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setExpanded((v) => !v);
          }}
          className="ml-1 uppercase font-mono"
          style={{
            fontSize: '9px',
            letterSpacing: '0.1em',
            color: 'var(--accent)',
            background: 'none',
            border: 'none',
            padding: 0,
            cursor: 'pointer',
          }}
        >
          {expanded ? 'less' : 'full route'}
        </button>
      )}
    </div>
  );
}

/**
 * Single truck card for the Transport tab.
 */
export default function TruckCard({
  truck,
  route,
  farmNames,
  dpNames,
  farmStops,
  totalLoad,
  distanceKm,
  loadPct,
  status,
  isSelected,
  onSelect,
  atRiskMap,
  mandiById,
  farmsById,
  computeETA,
  canReportBreakdown,
  onReportBreakdown,
  runId,
  livePosition,
  trackingEnabled,
}) {
  const label = displayTruckId(truck.id);
  const distancePending = !route || distanceKm <= 0;
  const distanceStr = distancePending ? null : `~${distanceKm.toFixed(0)} km`;
  const etaTime = distancePending ? null : computeETA(distanceKm);

  const statusLabel = status === 'broken_down' ? 'BROKEN DOWN'
    : status === 'deviating' ? 'DEVIATING'
      : status === 'assigned' ? 'ASSIGNED'
        : status === 'delayed' ? 'DELAYED' : 'IDLE';
  const statusColor = status === 'broken_down' ? 'var(--danger)'
    : status === 'deviating' ? 'var(--danger)'
      : status === 'assigned' ? 'var(--green-ok)'
        : status === 'delayed' ? 'var(--red-risk)' : 'var(--muted)';

  return (
    <article
      className="flex flex-col h-full p-5 md:p-6 font-mono"
      onClick={onSelect}
      style={{
        border: isSelected ? '2px solid var(--accent)' : '1px solid var(--border)',
        borderTop: isSelected ? '2px solid var(--accent)' : '3px solid var(--purple-log)',
        borderRadius: '4px',
        background: isSelected ? 'rgba(245, 166, 35, 0.06)' : 'var(--bg-card)',
        cursor: 'pointer',
        transition: 'border-color 0.2s ease, background 0.2s ease',
        minHeight: '200px',
      }}
    >
      <div className="flex items-start justify-between gap-3 mb-4 shrink-0">
        <p
          className="font-syne font-bold uppercase tracking-wider text-paper m-0"
          style={{ fontSize: '15px', letterSpacing: '0.06em' }}
        >
          {label}
        </p>
        <div className="flex items-center gap-2 flex-wrap justify-end shrink-0 font-mono">
          <span
            className="uppercase"
            style={{
              fontSize: '9px',
              letterSpacing: '0.15em',
              color: statusColor,
              border: `1px solid ${statusColor}`,
              borderRadius: '2px',
              padding: '2px 6px',
            }}
          >
            {statusLabel}
          </span>
          {isSelected && (
            <span
              className="uppercase"
              style={{
                fontSize: '9px',
                letterSpacing: '0.15em',
                color: 'var(--accent)',
                border: '1px solid var(--accent)',
                borderRadius: '2px',
                padding: '2px 6px',
              }}
            >
              SELECTED
            </span>
          )}
          <span className="text-muted" style={{ fontSize: '10px' }}>
            {truck.capacity_kg.toLocaleString()} kg cap
          </span>
        </div>
      </div>

      <div className="flex-1 flex flex-col gap-2 min-h-0">
        {route ? (
          <>
            <RouteLine farmNames={farmNames} dpNames={dpNames} />

            <p className="text-muted m-0 flex flex-wrap items-center gap-x-2 gap-y-1" style={{ fontSize: '11px' }}>
              <span>Distance:</span>
              {distancePending ? (
                <MetricSkeleton width="72px" />
              ) : (
                <span style={{ color: 'var(--text)' }}>{distanceStr}</span>
              )}
              <span aria-hidden>·</span>
              <span>ETA</span>
              {distancePending || etaTime === 'TBD' ? (
                <MetricSkeleton width="56px" />
              ) : (
                <span style={{ color: 'var(--text)' }}>{etaTime}</span>
              )}
              <span aria-hidden>·</span>
              <span style={{ color: 'var(--text)' }}>
                {Math.round(totalLoad).toLocaleString()} kg loaded
              </span>
            </p>

            <div className="mt-2">
              <div className="flex justify-between text-muted mb-1 font-mono" style={{ fontSize: '10px' }}>
                <span>LOAD</span>
                <span>
                  {Math.round(totalLoad).toLocaleString()} / {truck.capacity_kg.toLocaleString()} kg
                </span>
              </div>
              <div
                style={{
                  height: '4px',
                  background: 'var(--border)',
                  borderRadius: '2px',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${loadPct}%`,
                    height: '100%',
                    background: loadPct > 90 ? 'var(--red-risk)' : 'var(--purple-log)',
                    transition: 'width 0.4s ease',
                  }}
                />
              </div>
            </div>

            <WhyThisRoute
              stops={route.stops}
              atRiskMap={atRiskMap}
              mandiById={mandiById}
              farmsById={farmsById}
            />

            {livePosition && (
              <p className="text-muted m-0 mt-2" style={{ fontSize: '10px' }}>
                GPS: {(livePosition.status || 'unknown').replace('_', ' ').toUpperCase()}
                {' · '}
                {livePosition.deviation_km?.toFixed?.(1) ?? livePosition.deviation_km} km off route
              </p>
            )}

            {trackingEnabled && runId && route && (
              <Link
                href={`/driver/${runId}/${truck.id}`}
                onClick={(e) => e.stopPropagation()}
                className="mt-2 font-mono uppercase tracking-wider text-[10px] px-3 py-2 w-full inline-block text-center"
                style={{
                  border: '1px solid var(--accent)',
                  color: 'var(--accent)',
                  borderRadius: '2px',
                  textDecoration: 'none',
                }}
              >
                Open driver GPS page
              </Link>
            )}

            {canReportBreakdown && onReportBreakdown && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onReportBreakdown(truck.id, farmStops || []);
                }}
                className="mt-3 font-mono uppercase tracking-wider text-[10px] px-3 py-2 w-full"
                style={{
                  border: '1px solid var(--danger)',
                  color: 'var(--danger)',
                  borderRadius: '2px',
                  background: 'transparent',
                }}
              >
                Report breakdown
              </button>
            )}
          </>
        ) : (
          <p className="text-muted m-0 mt-auto" style={{ fontSize: '11px' }}>
            No route assigned in this plan.
          </p>
        )}
      </div>
    </article>
  );
}
