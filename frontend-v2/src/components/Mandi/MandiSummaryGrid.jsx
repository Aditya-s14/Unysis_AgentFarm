/**
 * Top-row mandi KPIs — same visual language as Overview KPIGrid.
 * All values come from summarizeMandiFulfilment + row counts (display only).
 */
export default function MandiSummaryGrid({ summary, shortageMandiCount, excessMandiCount }) {
  const s = summary || {};
  const netShortage = Number(s.netShortage) || 0;

  const tiles = [
    {
      title: 'Expected demand',
      value: `${(s.totalExpected || 0).toLocaleString()} kg`,
      subtitle: 'across all mandis',
      valueColor: 'var(--accent)',
    },
    {
      title: 'Incoming supply',
      value: `${(s.totalIncoming || 0).toLocaleString()} kg`,
      subtitle: 'on assigned trucks',
      valueColor: 'var(--text)',
    },
    {
      title: 'Current stock',
      value: `${(s.totalStock || 0).toLocaleString()} kg`,
      subtitle: 'at mandi yards',
      valueColor: 'var(--text)',
    },
    {
      title: 'Net shortage',
      value: `${netShortage.toLocaleString()} kg`,
      subtitle: netShortage > 0 ? 'aggregate gap' : 'no aggregate gap',
      valueColor: netShortage > 0 ? 'var(--accent)' : 'var(--green-ok)',
    },
    {
      title: 'Mandis with shortage',
      value: String(shortageMandiCount ?? 0),
      subtitle: `of ${s.mandiCount || 0} mandis`,
      valueColor: (shortageMandiCount ?? 0) > 0 ? 'var(--red-risk)' : 'var(--green-ok)',
    },
    {
      title: 'Mandis with excess',
      value: String(excessMandiCount ?? 0),
      subtitle: 'over expected demand',
      valueColor: 'var(--blue-mandi)',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
      {tiles.map((t) => (
        <div
          key={t.title}
          className="bg-card relative p-4 md:p-5"
          style={{
            border: '1px solid var(--border)',
            borderTop: '3px solid var(--accent)',
            borderRadius: '4px',
          }}
        >
          <p
            className="font-mono text-muted uppercase"
            style={{ fontSize: '0.65rem', letterSpacing: '0.12em' }}
          >
            {t.title}
          </p>
          <p
            className="font-syne font-bold leading-none mt-2"
            style={{ fontSize: '1.65rem', color: t.valueColor }}
          >
            {t.value}
          </p>
          <p
            className="mt-2 font-mono text-muted uppercase"
            style={{ fontSize: '10px', letterSpacing: '0.08em' }}
          >
            {t.subtitle}
          </p>
        </div>
      ))}
    </div>
  );
}
