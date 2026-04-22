import Head from 'next/head';
import { useState } from 'react';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import PlanViewer from '@/components/PlanViewer/PlanViewer';
import useRuns, { useRun, useRunTraces } from '@/hooks/useRuns';

/**
 * Runs page — left pane lists past runs, right pane shows the selected plan.
 */
export default function RunsPage() {
  const { data: runs, loading } = useRuns();
  const [selectedId, setSelectedId] = useState(null);
  const { data: run } = useRun(selectedId);
  const { data: traces } = useRunTraces(selectedId);

  return (
    <>
      <Head>
        <title>Runs | AgentFarm</title>
      </Head>
      <DashboardLayout title="Runs">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <aside className="lg:col-span-1 bg-white rounded-lg border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-200">
              <h2 className="font-semibold text-agri-green-dark text-sm">All Runs</h2>
            </div>
            {loading ? (
              <p className="p-4 text-sm text-gray-500">Loading...</p>
            ) : (
              <ul className="divide-y divide-gray-100">
                {runs.map((r) => (
                  <li key={r.runId}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(r.runId)}
                      className={`w-full text-left px-4 py-3 text-sm transition ${
                        selectedId === r.runId ? 'bg-agri-green-light/30' : 'hover:bg-gray-50'
                      }`}
                    >
                      <p className="font-medium">{r.runId}</p>
                      <p className="text-xs text-gray-500">{r.scenarioType}</p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </aside>

          <section className="lg:col-span-3">
            {selectedId ? (
              <PlanViewer run={run} traces={traces} />
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-8 text-center text-sm text-gray-500">
                Select a run from the list to view its plan.
              </div>
            )}
          </section>
        </div>
      </DashboardLayout>
    </>
  );
}
