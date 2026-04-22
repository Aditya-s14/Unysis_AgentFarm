import dynamic from 'next/dynamic';

/**
 * MapView — thin wrapper that dynamic-imports the inner Leaflet map with
 * SSR disabled. React-Leaflet accesses `window` on module load, so it cannot
 * be imported at the top of a Next.js page.
 */
const InnerMap = dynamic(() => import('./InnerMap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[480px] bg-gray-100 rounded-md flex items-center justify-center text-gray-500">
      Loading map...
    </div>
  ),
});

export default function MapView(props) {
  return (
    <div className="w-full h-[480px] rounded-md overflow-hidden border border-gray-200">
      <InnerMap {...props} />
    </div>
  );
}
