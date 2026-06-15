import Head from 'next/head';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import { useAppContext } from '@/context/AppContext';

/**
 * Placeholder for the per-role dashboards (T4 farmer / T5 driver / T6 mandi,
 * owned by Member B). Proves the F2 route guard end-to-end and surfaces the
 * JWT identity the real dashboard will personalize from.
 */
export default function RolePlaceholder({ role, title, taskRef, description }) {
  const { user } = useAppContext();

  return (
    <>
      <Head><title>{title} | AgentFarm</title></Head>
      <DashboardLayout title={title} subtitle={`${taskRef} · placeholder`}>
        <div className="glass-card-static p-10 text-center max-w-2xl mx-auto">
          <div
            className="w-14 h-14 rounded-xl mx-auto mb-4 flex items-center justify-center"
            style={{ background: 'var(--accent-muted)' }}
          >
            <span className="text-xl" aria-hidden>🔒</span>
          </div>
          <p className="text-sm font-semibold mb-2" style={{ color: 'var(--navy)' }}>
            {title} — guarded route for role “{role}”
          </p>
          <p className="text-xs mb-5" style={{ color: 'var(--text-tertiary)' }}>
            {description} Full UI lands with {taskRef} (Member B).
          </p>
          {user && (
            <div
              className="inline-block text-left text-xs px-4 py-3 rounded-lg"
              style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border)' }}
            >
              <p style={{ color: 'var(--text-secondary)' }}>
                Signed in as <strong style={{ color: 'var(--navy)' }}>{user.name || user.phone}</strong>
              </p>
              <p style={{ color: 'var(--text-secondary)' }}>
                Role: <strong style={{ color: 'var(--accent)' }}>{user.role}</strong>
                {user.entityId && (
                  <>
                    {' '}· Entity: <strong style={{ color: 'var(--accent)' }}>{user.entityId}</strong>
                  </>
                )}
              </p>
            </div>
          )}
        </div>
      </DashboardLayout>
    </>
  );
}
