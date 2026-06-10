import RolePlaceholder from '@/components/Dashboard/RolePlaceholder';

/** Farmer dashboard mount point (T4) — single-farm view from JWT entity_id. */
export default function FarmerPage() {
  return (
    <RolePlaceholder
      role="farmer"
      title="Farmer Dashboard"
      taskRef="T4"
      description="Weather + forecast for your farm, crop-ready toggle, assigned truck ETA, and arrival confirmation."
    />
  );
}
