import Head from 'next/head';
import Link from 'next/link';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import OverviewPanel from '@/components/Dashboard/OverviewPanel';
import KPIGrid from '@/components/KPICards/KPIGrid';
import useRuns from '@/hooks/useRuns';

/**
 * Dashboard — main landing surface after entering the app.
 * Shows KPIs for the most recent run plus a list of recent runs.
 */
export default function DashboardPage() {
  const { data: runs, loading } = useRuns();
  const lastRun = runs?.[runs.length - 1];

  return (
    <>
      <Head>
        <title>Dashboard | AgentFarm</title>
      </Head>
      <DashboardLayout title="Dashboard">
        <OverviewPanel lastRun={lastRun} />
        {/* TODO: wire KPI values from the actual latest run payload. */}
        <KPIGrid />

        <section className="mt-8 bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="px-5 py-3 border-b border-gray-200 flex justify-between">
            <h2 className="font-semibold text-agri-green-dark">Recent Runs</h2>
            <Link href="/runs" className="text-sm text-agri-green hover:underline">
              View all
            </Link>
          </div>
          {loading ? (
            <p className="p-5 text-sm text-gray-500">Loading...</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {runs.map((r) => (
                <li
                  key={r.runId}
                  className="px-5 py-3 flex justify-between items-center text-sm"
                >
                  <div>
                    <p className="font-medium">{r.runId}</p>
                    <p className="text-xs text-gray-500">{r.scenarioType}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">{r.createdAt}</p>
                    <p className="text-xs text-green-700">
                      {(r.wasteReductionPct * 100).toFixed(1)}% waste reduction
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </DashboardLayout>
    </>
  );
}
