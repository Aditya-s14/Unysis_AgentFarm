import RolePlaceholder from '@/components/Dashboard/RolePlaceholder';

/** Mandi dashboard mount point (T6) — stock vs demand, arrivals, confirmations. */
export default function MandiPage() {
  return (
    <RolePlaceholder
      role="mandi"
      title="Mandi Dashboard"
      taskRef="T6"
      description="Current stock vs required, truck arrival ETAs, and delivery confirmation into plan_outcomes."
    />
  );
}
