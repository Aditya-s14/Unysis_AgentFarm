#!/usr/bin/env bash
# Pre-demo health check: Docker services, DB seed counts, API health, minimal scenario run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> docker compose ps"
docker compose ps

echo "==> backend health"
curl -sf http://localhost:8000/health | grep -q '"status":"ok"' || {
  echo "FAIL: /health did not return ok"
  exit 1
}

echo "==> database seed counts"
FARMS="$(docker exec agentfarm_postgres psql -U agentfarm -d agentfarm -t -A -c 'SELECT COUNT(*) FROM farms;')"
OUTCOMES="$(docker exec agentfarm_postgres psql -U agentfarm -d agentfarm -t -A -c 'SELECT COUNT(*) FROM plan_outcomes;')"
echo "farms=$FARMS plan_outcomes=$OUTCOMES"
[ "$FARMS" -ge 20 ] || { echo "FAIL: expected >= 20 farms"; exit 1; }
[ "$OUTCOMES" -ge 40 ] || { echo "FAIL: expected >= 40 plan_outcomes"; exit 1; }

echo "==> minimal scenario run"
RESP="$(curl -sf -X POST http://localhost:8000/api/scenario/run \
  -H 'Content-Type: application/json' \
  -d @scripts/validate_demo_payload.json)"
echo "$RESP" | grep -q '"run_id"' || {
  echo "FAIL: scenario run missing run_id"
  exit 1
}

echo "PASS: demo stack is healthy"
