import { useRouter } from 'next/router';
import ScenarioTypeSelect, { ScenarioPipelinePreview } from './ScenarioTypeSelect';
import useScenario from '@/hooks/useScenario';
import { getBuyerDemandsForApi } from '@/hooks/useBuyerDemands';
import { getMarketCommitmentsForApi } from '@/hooks/useMarketOffers';
import { useAppContext } from '@/context/AppContext';
import {
  DEMO_FARMS,
  DEMO_DEMAND_POINTS,
  DEMO_TRUCKS,
} from '@/utils/demoFixtures';

/**
 * ScenarioForm — pick a disruption template and run the backend pipeline.
 *
 * Demo fixture: 20 farms (Karnataka + Maharashtra), 10 mandis, 10 trucks.
 */
export default function ScenarioForm({ onRunStart, onComplete, onError }) {
  const router = useRouter();
  const { scenarioDraft, setScenarioDraft, setCurrentRunId } = useAppContext();
  const { run, loading, error } = useScenario();

  const handleSubmit = async (e) => {
    e.preventDefault();
    onRunStart?.(scenarioDraft.scenarioType);
    const buyer_demands = getBuyerDemandsForApi();
    const market_commitments = getMarketCommitmentsForApi();
    const body = {
      scenario_type: scenarioDraft.scenarioType,
      farms: DEMO_FARMS,
      demand_points: DEMO_DEMAND_POINTS,
      trucks: DEMO_TRUCKS,
      farmer_commitments: [],
      buyer_demands,
      market_commitments,
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
        farmer_commitments: [],
        buyer_demands,
        market_commitments,
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

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <ScenarioTypeSelect
        value={scenarioDraft.scenarioType}
        onChange={(val) => setScenarioDraft({ ...scenarioDraft, scenarioType: val })}
        layout="cards"
      />

      <ScenarioPipelinePreview />

      {error && (
        <div
          className="font-mono text-[12px] p-3"
          style={{
            color: 'var(--red-risk)',
            border: '1px solid var(--red-risk)',
            background: 'var(--red-muted)',
            borderRadius: '2px',
          }}
        >
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full py-3.5 font-mono uppercase tracking-wider-2 transition disabled:opacity-50"
        style={{
          background: loading ? 'var(--border)' : 'var(--accent)',
          color: loading ? 'var(--muted)' : 'var(--accent-text)',
          fontSize: '12px',
          fontWeight: 600,
          borderRadius: '4px',
          letterSpacing: '0.15em',
          border: 'none',
        }}
      >
        {loading ? '◦ Running agent pipeline…' : 'Run Scenario →'}
      </button>
    </form>
  );
}
