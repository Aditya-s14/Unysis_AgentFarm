import Head from 'next/head';
import { useEffect, useMemo } from 'react';
import { useRouter } from 'next/router';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import withAuth from '@/components/withAuth';
import { useAppContext } from '@/context/AppContext';
import { displayTruckId } from '@/utils/truckDisplay';

const CARD = {
  border: '1px solid var(--border)',
  borderRadius: '4px',
  background: 'var(--bg-card)',
};

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
      <DashboardLayout title="No active route" subtitle={truckLabel}>
        <div className="space-y-6 max-w-xl">
          <div className="p-5" style={CARD}>
            <p className="font-mono uppercase text-[10px] tracking-widest mb-3" style={{ color: 'var(--muted)' }}>
              Route status
            </p>
            <p className="font-syne font-bold text-[15px]" style={{ color: 'var(--navy)' }}>
              Waiting for assignment
            </p>
            <p className="font-mono text-[12px] mt-2" style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              There is no scenario run assigned yet. Ask your FPO coordinator to run a plan first,
              then return here or sign in again.
            </p>
          </div>
          <div className="p-5" style={CARD}>
            <p className="font-mono uppercase text-[10px] tracking-widest mb-2" style={{ color: 'var(--muted)' }}>
              Assigned truck
            </p>
            <p className="font-syne font-bold text-[18px]" style={{ color: 'var(--forest)' }}>
              {truckLabel}
            </p>
          </div>
        </div>
      </DashboardLayout>
    </>
  );
}

export default withAuth(DriverHomePage, ['driver']);
