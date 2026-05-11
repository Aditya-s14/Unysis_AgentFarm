import dynamic from 'next/dynamic';

/**
 * MapView — thin wrapper that dynamic-imports the inner Leaflet map with
 * SSR disabled. React-Leaflet accesses `window` on module load, so it cannot
 * be imported at the top of a Next.js page.
 */
const InnerMap = dynamic(() => import('./InnerMap'), {
  ssr: false,
  loading: () => (
    <div
      className="w-full h-[480px] flex items-center justify-center font-mono text-muted text-[12px] tracking-wider-2"
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: '4px',
      }}
    >
      ◦ Loading map…
    </div>
  ),
});

export default function MapView(props) {
  return (
    <div
      className="w-full h-[480px] overflow-hidden"
      style={{
        border: '1px solid var(--border)',
        borderRadius: '4px',
      }}
    >
      <InnerMap {...props} />
    </div>
  );
}
