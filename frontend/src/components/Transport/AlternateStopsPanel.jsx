import { DEMO_FARMS } from '@/utils/demoFixtures';

const RISK_COLORS = { severe: '#FF4444', warning: '#FF9800' };

/**
 * AlternateStopsPanel — shows at-risk farms not currently on this truck's route
 * that could be re-routed to if conditions change. Derived from at_risk_stock data.
 */
export default function AlternateStopsPanel({ planData, currentStops = [] }) {
  if (!planData) return null;

  const currentFarmIds = new Set(
    currentStops.filter((s) => !s.demand_point_id).map((s) => s.label).filter(Boolean)
  );

  const atRisk = (planData.at_risk_stock || []).filter(
    (s) => !currentFarmIds.has(s.farm_id) && s.hours_until_spoilage != null && s.hours_until_spoilage < 48
  );

  if (atRisk.length === 0) return null;

  const suggestions = atRisk
    .sort((a, b) => (a.hours_until_spoilage ?? 99) - (b.hours_until_spoilage ?? 99))
    .slice(0, 3)
    .map((s) => {
      const farm = DEMO_FARMS.find((f) => f.id === s.farm_id);
      const risk = s.hours_until_spoilage < 24 ? 'severe' : 'warning';
      return { ...s, farm, risk };
    });

  return (
    <div className="mb-4">
      <p className="text-[10px] uppercase tracking-widest mb-2" style={{ color: 'var(--muted)' }}>
        Alternate Stop Suggestions ({suggestions.length})
      </p>
      <div
        className="p-3"
        style={{
          border: '1px solid var(--border)',
          borderRadius: '4px',
          background: 'rgba(255,152,0,0.04)',
        }}
      >
        <p className="text-[11px] mb-3" style={{ color: 'var(--muted)' }}>
          High-risk farms not on your current route. Contact FPO to reroute.
        </p>
        <div className="space-y-2">
          {suggestions.map((s) => (
            <div
              key={s.farm_id}
              className="flex items-start gap-3 p-2"
              style={{
                border: `1px solid ${RISK_COLORS[s.risk]}30`,
                borderRadius: '3px',
                background: `rgba(${s.risk === 'severe' ? '220,50,50' : '255,152,0'},0.06)`,
              }}
            >
              <span style={{ color: RISK_COLORS[s.risk], fontSize: 14, flexShrink: 0, marginTop: 1 }}>⚠</span>
              <div className="flex-1 min-w-0">
                <p className="text-[12px] font-bold" style={{ color: 'var(--text)' }}>
                  {s.farm?.name || s.farm_id}
                </p>
                <p className="text-[10px] mt-0.5" style={{ color: RISK_COLORS[s.risk] }}>
                  {s.risk.toUpperCase()} · {Math.round(s.hours_until_spoilage)}h until spoilage
                </p>
                <p className="text-[10px] mt-0.5" style={{ color: 'var(--muted)' }}>
                  {s.farm?.crop_type?.toUpperCase() || 'CROP'}
                  {s.kg_at_risk ? ` · ${s.kg_at_risk.toLocaleString()} kg at risk` : ''}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
