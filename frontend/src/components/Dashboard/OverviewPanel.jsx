/**
 * OverviewPanel — a simple descriptive banner used at the top of the dashboard.
 * Shows system status and a short summary of the most recent run.
 */
export default function OverviewPanel({ lastRun }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm mb-6">
      <div className="flex flex-wrap justify-between gap-4">
        <div>
          <h2 className="font-semibold text-agri-green-dark">System Overview</h2>
          <p className="text-sm text-gray-600 mt-1">
            Six autonomous agents currently monitoring 20 farms, 10 mandis, and 10 trucks.
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase text-gray-500 tracking-wide">Last Run</p>
          <p className="text-sm font-medium text-gray-800">
            {lastRun?.runId || 'No runs yet'}
          </p>
          <p className="text-xs text-gray-500">
            {lastRun?.createdAt || 'Run a scenario to populate'}
          </p>
        </div>
      </div>
    </div>
  );
}
