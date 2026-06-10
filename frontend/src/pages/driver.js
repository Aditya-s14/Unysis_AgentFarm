import RolePlaceholder from '@/components/Dashboard/RolePlaceholder';

/** Driver dashboard mount point (T5) — own truck stops, ETAs, reroutes (R4). */
export default function DriverPage() {
  return (
    <RolePlaceholder
      role="driver"
      title="Driver Dashboard"
      taskRef="T5"
      description="Your stop sequence, weather along the path, per-stop countdown, and alternate-route suggestions."
    />
  );
}
