import { useRouter } from 'next/router';
import ScenarioTypeSelect from './ScenarioTypeSelect';
import useScenario from '@/hooks/useScenario';
import { useAppContext } from '@/context/AppContext';
import {
  DEMO_FARMS,
  DEMO_DEMAND_POINTS,
  DEMO_TRUCKS,
  DEMO_TRUCKS_CAPACITY_STRESS,
} from '@/utils/demoFixtures';

/**
 * ScenarioForm — pick a disruption template and run the backend pipeline.
 *
 * Demo fixture: 20 farms (Karnataka + Maharashtra), 10 mandis, 10 trucks.
 * Only `scenario_type` and (for capacity_stress) truck fleet differ between runs.
 */
export default function ScenarioForm({ onRunStart, onComplete, onError }) {
  const router = useRouter();
  const { scenarioDraft, setScenarioDraft, setCurrentRunId } = useAppContext();
  const { run, loading, error } = useScenario();

  const handleSubmit = async (e) => {
    e.preventDefault();
    onRunStart?.(scenarioDraft.scenarioType);
    const trucks = scenarioDraft.scenarioType === 'capacity_stress'
      ? DEMO_TRUCKS_CAPACITY_STRESS
      : DEMO_TRUCKS;
    const body = {
      scenario_type: scenarioDraft.scenarioType,
      farms: DEMO_FARMS,
      demand_points: DEMO_DEMAND_POINTS,
      trucks,
    };
    try {
      const result = await run(body);
      if (!result?.run_id) {
        throw new Error('Pipeline completed without a run_id — check backend logs');
      }
      setCurrentRunId(result.run_id);
      const scenarioResult = {
        ...result,
        scenario_type: body.scenario_type,
        farms: body.farms,
        demand_points: body.demand_points,
      };
      if (typeof window !== 'undefined') {
        try {
          window.localStorage.setItem(
            'agentfarm_last_response',
            JSON.stringify(scenarioResult),
          );
        } catch {
          /* localStorage full / disabled — non-fatal */
        }
      }
      if (typeof onComplete === 'function') {
        onComplete(scenarioResult);
      } else {
        router.push('/dashboard');
      }
    } catch (err) {
      onError?.(err);
    }
  };

  const previewTrucks = scenarioDraft.scenarioType === 'capacity_stress'
    ? DEMO_TRUCKS_CAPACITY_STRESS
    : DEMO_TRUCKS;
  const totalCapacity = previewTrucks.reduce((s, t) => s + t.capacity_kg, 0);

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
          <span className="text-muted">farms (Karnataka + Maharashtra)</span>{' '}
          ·{' '}
          <span className="text-accent">{DEMO_DEMAND_POINTS.length}</span>{' '}
          <span className="text-muted">mandis</span>{' '}
          ·{' '}
          <span className="text-accent">{previewTrucks.length}</span>{' '}
          <span className="text-muted">
            trucks ({totalCapacity.toLocaleString()} kg total capacity)
          </span>
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
