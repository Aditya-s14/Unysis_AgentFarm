/**
 * ScenarioTypeSelect — dropdown choosing between the supported
 * disruption templates (monsoon / heat wave).
 */
export default function ScenarioTypeSelect({ value, onChange }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-gray-700">Scenario Type</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-agri-green"
      >
        <option value="monsoon_disruption">Monsoon Disruption</option>
        <option value="heat_wave">Heat Wave</option>
      </select>
    </label>
  );
}
