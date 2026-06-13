import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAppContext } from '@/context/AppContext';

/** Redirect /driver → /driver/[runId]/[truckId] using stored run + user entity */
export default function DriverPage() {
  const router = useRouter();
  const { user } = useAppContext();

  useEffect(() => {
    if (!user) { router.replace('/login'); return; }
    let runId = null;
    if (typeof window !== 'undefined') {
      runId = localStorage.getItem('agentfarm_run_id');
      if (!runId) {
        try {
          const cached = JSON.parse(localStorage.getItem('agentfarm_last_response') || '{}');
          runId = cached?.run_id || null;
        } catch { /* ignore */ }
      }
    }
    if (runId && user.entityId) {
      router.replace(`/driver/${runId}/${user.entityId}`);
    } else {
      router.replace('/runs');
    }
  }, [user, router]);

  return null;
}
