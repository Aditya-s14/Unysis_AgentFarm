import { useState } from 'react';
import ScenarioTypeSelect from './ScenarioTypeSelect';
import useScenario from '@/hooks/useScenario';
import { useAppContext } from '@/context/AppContext';

/**
 * ScenarioForm — lets the user pick a disruption template, optionally upload
 * CSVs for farms/demand/trucks, and kick off the backend pipeline.
 */
export default function ScenarioForm({ onComplete }) {
  const { scenarioDraft, setScenarioDraft, setCurrentRunId } = useAppContext();
  const { run, loading, error } = useScenario();
  const [csvFile, setCsvFile] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    // TODO: parse CSV client-side or upload to backend; for now we send an
    // empty body and let the backend use seed data.
    const body = {
      scenarioType: scenarioDraft.scenarioType,
      farms: scenarioDraft.farms,
      demandPoints: scenarioDraft.demandPoints,
      trucks: scenarioDraft.trucks,
      constraints: scenarioDraft.constraints,
    };
    try {
      const result = await run(body);
      if (result?.runId) {
        setCurrentRunId(result.runId);
      }
      onComplete?.(result);
    } catch {
      // error captured inside the hook
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm space-y-4"
    >
      <ScenarioTypeSelect
        value={scenarioDraft.scenarioType}
        onChange={(val) => setScenarioDraft({ ...scenarioDraft, scenarioType: val })}
      />

      <div>
        <span className="text-sm font-medium text-gray-700">Upload CSV (farms / demand / trucks)</span>
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
          className="mt-1 block w-full text-sm text-gray-600"
        />
        <p className="mt-1 text-xs text-gray-500">
          {csvFile ? `Selected: ${csvFile.name}` : 'Optional — leave blank to use seed data (TODO: wire to backend).'}
        </p>
      </div>

      {error && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full px-4 py-2 rounded-md bg-agri-green text-white font-medium hover:bg-agri-green-dark transition disabled:opacity-60"
      >
        {loading ? 'Running pipeline...' : 'Run Scenario'}
      </button>
    </form>
  );
}
