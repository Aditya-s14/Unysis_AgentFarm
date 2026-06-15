import { useEffect, useMemo, useState } from 'react';
import {
  Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { getSeasonTrends } from '@/api/client';
import { API_BASE_URL } from '@/utils/api';
import { EM_DASH, SECTION } from '@/utils/uiChars';

const METRICS = [
  {
    key: 'waste_reduction_pct',
    label: 'Waste reduction',
    unit: '%',
    color: 'var(--green-ok)',
    subtitle: 'Tier-2 actuals — predicted vs observed waste (kg)',
  },
  {
    key: 'forecast_accuracy_pct',
    label: 'Forecast accuracy',
    unit: '%',
    color: 'var(--accent)',
    subtitle: 'Demand predicted vs actual at mandi',
  },
  {
    key: 'delivery_accuracy_pct',
    label: 'Delivery accuracy',
    unit: '%',
    color: '#64B5F6',
    subtitle: 'Route time predicted vs actual',
  },
];

function TrendChart({ seasons, metricKey, label, unit, color, subtitle }) {
  const data = seasons.map((s) => ({
    season: s.season.replace(' ', '\n'),
    value: Number(s[metricKey] ?? 0),
    learning_note: s.learning_note,
  }));

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const row = payload[0].payload;
    return (
      <div
        className="font-mono"
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: '4px',
          padding: '8px 12px',
          fontSize: '11px',
          color: 'var(--text)',
        }}
      >
        <p style={{ color: 'var(--muted)' }}>{row.season.replace('\n', ' ')}</p>
        <p style={{ color, fontWeight: 700 }}>
          {Number(row.value).toFixed(1)}{unit}
        </p>
        <p style={{ color: 'var(--muted)', marginTop: 4 }}>{row.learning_note}</p>
      </div>
    );
  };

  return (
    <div
      className="flex-1 min-w-[200px]"
      style={{ border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg)' }}
    >
      <div className="px-3 py-2" style={{ borderBottom: '1px solid var(--border)' }}>
        <p className="font-mono uppercase" style={{ fontSize: '10px', color, letterSpacing: '0.12em' }}>
          {label}
        </p>
        <p className="font-mono text-muted mt-0.5" style={{ fontSize: '9px' }}>{subtitle}</p>
      </div>
      <div className="px-2 py-3" style={{ height: '160px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barCategoryGap="25%" margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <XAxis
              dataKey="season"
              tick={{ fill: 'var(--muted)', fontFamily: 'IBM Plex Sans', fontSize: 9 }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
              interval={0}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: 'var(--muted)', fontFamily: 'IBM Plex Sans', fontSize: 9 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v}%`}
              width={36}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--bg-subtle)' }} />
            <Bar dataKey="value" radius={[2, 2, 0, 0]}>
              {data.map((entry) => (
                <Cell key={entry.season} fill={color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function DeltaBadge({ latest, prior, metricKey, unit }) {
  if (!latest || !prior) return null;
  const delta = Number(latest[metricKey]) - Number(prior[metricKey]);
  if (!Number.isFinite(delta)) return null;
  const sign = delta >= 0 ? '+' : '';
  return (
    <span className="font-mono" style={{ fontSize: '10px', color: 'var(--green-ok)' }}>
      {sign}{delta.toFixed(1)}{unit} vs {prior.season}
    </span>
  );
}

/**
 * Season-over-season Tier-2 learning trends (outcome actuals, not optimizer KPIs).
 */
export default function SeasonTrendPanel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getSeasonTrends()
      .then(setData)
      .catch((err) => setError(err?.message || 'Failed to load season trends'));
  }, []);

  const seasons = data?.seasons ?? [];
  const latest = seasons[seasons.length - 1];
  const prior = seasons[seasons.length - 2];

  const exportUrl = useMemo(
    () => `${API_BASE_URL}/analytics/season-trends/export`,
    [],
  );

  if (error) {
    return (
      <div className="mt-6 font-mono text-muted" style={{ fontSize: '11px' }}>
        Season trends unavailable: {error}
      </div>
    );
  }

  if (!seasons.length) {
    return null;
  }

  return (
    <div
      className="mt-6 bg-card"
      style={{ border: '1px solid var(--border)', borderRadius: '4px', overflow: 'hidden' }}
    >
      <div
        className="px-5 py-3 flex flex-wrap items-baseline justify-between gap-2"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <div>
          <h2
            className="font-syne font-bold uppercase text-paper tracking-wider-2"
            style={{ fontSize: '14px' }}
          >
            {`${SECTION} Tier-2 Learning ${EM_DASH} Season Trends`}
          </h2>
          <p className="font-mono text-muted mt-1" style={{ fontSize: '10px', lineHeight: 1.5 }}>
            Outcome actuals from delivery confirmations feed demand and logistics bias correction.
            {' '}
            {data?.tier2_outcome_total ?? 0} logged outcomes across {seasons.length} seasons.
          </p>
        </div>
        <a
          href={exportUrl}
          className="font-mono uppercase tracking-wider-2 hover:text-accent transition"
          style={{ fontSize: '10px', color: 'var(--muted)', letterSpacing: '0.12em' }}
          download="season_trends.csv"
        >
          Export CSV
        </a>
      </div>

      {latest && (
        <div className="px-5 py-2 flex flex-wrap gap-4" style={{ borderBottom: '1px solid var(--border)' }}>
          <span className="font-mono" style={{ fontSize: '10px', color: 'var(--accent)' }}>
            {latest.season}: {latest.learning_note}
          </span>
          {METRICS.map((m) => (
            <DeltaBadge
              key={m.key}
              latest={latest}
              prior={prior}
              metricKey={m.key}
              unit={m.unit}
            />
          ))}
        </div>
      )}

      <div className="px-4 py-4 flex flex-col lg:flex-row gap-4">
        {METRICS.map((m) => (
          <TrendChart
            key={m.key}
            seasons={seasons}
            metricKey={m.key}
            label={m.label}
            unit={m.unit}
            color={m.color}
            subtitle={m.subtitle}
          />
        ))}
      </div>
    </div>
  );
}
