import Head from 'next/head';
import { useEffect, useMemo } from 'react';
import { useRouter } from 'next/router';
import DriverSidebar, { SIDEBAR_WIDTH } from '@/components/Driver/DriverSidebar';
import withAuth from '@/components/withAuth';
import { useAppContext } from '@/context/AppContext';
import { displayTruckId } from '@/utils/truckDisplay';

function DriverHomePage() {
  const router = useRouter();
  const { user } = useAppContext();

  const runId = useMemo(() => {
    if (typeof window === 'undefined') return null;
    const stored = localStorage.getItem('agentfarm_run_id');
    if (stored) return stored;
    try {
      const cached = JSON.parse(localStorage.getItem('agentfarm_last_response') || '{}');
      return cached?.run_id || null;
    } catch {
      return null;
    }
  }, []);

  const routeHref = runId && user?.entityId
    ? `/driver/${runId}/${user.entityId}`
    : null;

  useEffect(() => {
    if (routeHref) {
      router.replace(routeHref);
    }
  }, [routeHref, router]);

  if (routeHref) return null;

  const truckLabel = user?.entityId ? displayTruckId(user.entityId) : 'Truck';

  return (
    <>
      <Head><title>Driver | AgentFarm</title></Head>
      <div className="flex min-h-screen" style={{ background: 'var(--bg)', color: 'var(--text)' }}>
        <DriverSidebar truckLabel={truckLabel} />
        <main
          className="flex-1 min-h-screen p-8 font-mono"
          style={{ marginLeft: SIDEBAR_WIDTH }}
        >
          <h1 className="font-syne font-bold text-paper" style={{ fontSize: '18px' }}>
            No active route
          </h1>
          <p className="font-mono text-muted mt-2" style={{ fontSize: '12px', lineHeight: 1.6 }}>
            There is no scenario run assigned yet. Ask your FPO coordinator to run a plan first,
            then return here or sign in again.
          </p>
          <p className="font-mono text-muted mt-4" style={{ fontSize: '11px' }}>
            Assigned truck: {truckLabel}
          </p>
        </main>
      </div>
    </>
  );
}

export default withAuth(DriverHomePage, ['driver']);
