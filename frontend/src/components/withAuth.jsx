import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAppContext } from '@/context/AppContext';

const ROLE_HOME = {
  fpo:    '/dashboard',
  farmer: '/farmer',
  driver: null, // dynamic â€” needs run context
  mandi:  '/mandi',
};

/**
 * HOC that protects a page behind authentication and optional role check.
 * Usage: export default withAuth(MyPage, ['farmer', 'fpo'])
 *        export default withAuth(MyPage)  // any authenticated user
 */
export default function withAuth(WrappedComponent, allowedRoles = null) {
  function AuthGuard(props) {
    const { user } = useAppContext();
    const loading = false;
    const router = useRouter();

    useEffect(() => {
      if (loading) return;

      if (!user) {
        router.replace('/login');
        return;
      }

      if (allowedRoles && !allowedRoles.includes(user.role)) {
        // Redirect to the page appropriate for their role
        const home = ROLE_HOME[user.role];
        if (home) {
          router.replace(home);
        } else if (user.role === 'driver') {
          // Driver needs a runId â€” go to /runs to pick one, or / if no run
          const runId = typeof window !== 'undefined'
            ? localStorage.getItem('agentfarm_run_id')
            : null;
          if (runId) {
            router.replace(`/driver/${runId}/${user.entity_id}`);
          } else {
            router.replace('/runs');
          }
        }
      }
    }, [user, loading, router]);

    if (loading) {
      return (
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
          <div style={{ textAlign: 'center' }}>
            <div className="dot-live" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>Loading...</p>
          </div>
        </div>
      );
    }

    if (!user) return null;
    if (allowedRoles && !allowedRoles.includes(user.role)) return null;

    return <WrappedComponent {...props} />;
  }

  AuthGuard.displayName = `withAuth(${WrappedComponent.displayName || WrappedComponent.name || 'Component'})`;
  return AuthGuard;
}

