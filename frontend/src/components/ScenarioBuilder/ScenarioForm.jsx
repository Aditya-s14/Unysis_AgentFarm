import { useState } from 'react';
import { useRouter } from 'next/router';
import ScenarioTypeSelect from './ScenarioTypeSelect';
import useScenario from '@/hooks/useScenario';
import { useAppContext } from '@/context/AppContext';
import {
  DEMO_FARMS,
  DEMO_DEMAND_POINTS,
  DEMO_TRUCKS,
} from '@/utils/demoFixtures';

/**
 * ScenarioForm — lets the user pick a disruption template, optionally upload
 * CSVs for farms/demand/trucks, and kick off the backend pipeline.
 *
 * For the demo, every scenario type uses the same 3-farm Bengaluru cluster
 * (see demoFixtures.js).  Only `scenario_type` varies between runs.
 */
/**
 * onRunStart  — called immediately when the user hits submit (before the API call).
 * onComplete  — called with the API result; when provided, navigation is suppressed
 *               so the parent page can drive the post-run flow.
 * onError     — called with the error when the pipeline call fails; lets the parent
 *               page show a top-level error state instead of the hidden inline error.
 */
export default function ScenarioForm({ onRunStart, onComplete, onError }) {
  const router = useRouter();
  const { scenarioDraft, setScenarioDraft, setCurrentRunId } = useAppContext();
  const { run, loading, error } = useScenario();
  const [csvFile, setCsvFile] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    onRunStart?.();
    const body = {
      scenario_type: scenarioDraft.scenarioType,
      farms: DEMO_FARMS,
      demand_points: DEMO_DEMAND_POINTS,
      trucks: DEMO_TRUCKS,
    };
    try {
      const result = await run(body);
      if (result?.run_id) {
        setCurrentRunId(result.run_id);
        if (typeof window !== 'undefined') {
          try {
            const enriched = { ...result, scenario_type: body.scenario_type };
            window.localStorage.setItem(
              'agentfarm_last_response',
              JSON.stringify(enriched),
            );
          } catch {
            /* localStorage full / disabled — non-fatal */
          }
        }
        if (typeof onComplete === 'function') {
          onComplete(result);
        } else {
          router.push('/dashboard');
        }
      }
    } catch (err) {
      onError?.(err);
      /* error also captured inside the hook for inline display */
    }
  };

  const totalCapacity = DEMO_TRUCKS.reduce((s, t) => s + t.capacity_kg, 0);

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-card p-6 space-y-6"
      style={{
        border: '1px solid var(--border)',
        borderRadius: '4px',
      }}
    >
      <ScenarioTypeSelect
        value={scenarioDraft.scenarioType}
        onChange={(val) => setScenarioDraft({ ...scenarioDraft, scenarioType: val })}
      />

      <div
        className="p-4"
        style={{
          background: 'rgba(245, 166, 35, 0.03)',
          border: '1px solid var(--border)',
          borderRadius: '4px',
        }}
      >
        <p
          className="font-mono uppercase mb-2"
          style={{
            color: 'var(--accent)',
            fontSize: '0.65rem',
            letterSpacing: '0.15em',
          }}
        >
          ▸ Demo Fixture
        </p>
        <p className="font-mono text-paper text-[12px] leading-relaxed">
          <span className="text-accent">{DEMO_FARMS.length}</span>{' '}
          <span className="text-muted">farms (Bengaluru cluster)</span>{' '}
          ·{' '}
          <span className="text-accent">{DEMO_DEMAND_POINTS.length}</span>{' '}
          <span className="text-muted">APMC mandis</span>{' '}
          ·{' '}
          <span className="text-accent">{DEMO_TRUCKS.length}</span>{' '}
          <span className="text-muted">trucks ({totalCapacity.toLocaleString()} kg total capacity)</span>
        </p>
      </div>

      <div>
        <p
          className="font-mono text-muted uppercase mb-2"
          style={{ fontSize: '0.7rem', letterSpacing: '0.1em' }}
        >
          Upload CSV (optional)
        </p>
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
          className="block w-full text-[12px] text-muted font-mono file:mr-3 file:py-1.5 file:px-3 file:border file:border-line file:bg-transparent file:text-muted file:font-mono file:text-[11px] file:tracking-wider hover:file:text-accent hover:file:border-accent file:cursor-pointer"
        />
        <p className="mt-2 font-mono text-muted text-[11px]">
          {csvFile ? `Selected: ${csvFile.name}` : 'Leave blank to use the demo fixture above.'}
        </p>
      </div>

      {error && (
        <div
          className="font-mono text-[12px] p-3"
          style={{
            color: 'var(--red-risk)',
            border: '1px solid var(--red-risk)',
            background: 'rgba(255, 68, 68, 0.05)',
            borderRadius: '2px',
          }}
        >
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 font-mono uppercase tracking-wider-2 transition disabled:opacity-50"
        style={{
          background: 'var(--accent)',
          color: '#0D1F0F',
          fontSize: '12px',
          fontWeight: 600,
          borderRadius: '2px',
          letterSpacing: '0.15em',
        }}
      >
        {loading ? '◦ Running pipeline…' : 'Run Scenario →'}
      </button>
    </form>
  );
}
