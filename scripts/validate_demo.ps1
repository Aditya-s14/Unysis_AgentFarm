# Pre-demo health check (Windows): Docker services, DB seed, API health, minimal scenario.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> docker compose ps"
docker compose ps

Write-Host "==> backend health"
$health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
if ($health.status -ne "ok") { throw "FAIL: /health did not return ok" }

Write-Host "==> database seed counts"
$farms = (docker exec agentfarm_postgres psql -U agentfarm -d agentfarm -t -A -c "SELECT COUNT(*) FROM farms;").Trim()
$outcomes = (docker exec agentfarm_postgres psql -U agentfarm -d agentfarm -t -A -c "SELECT COUNT(*) FROM plan_outcomes;").Trim()
Write-Host "farms=$farms plan_outcomes=$outcomes"
if ([int]$farms -lt 20) { throw "FAIL: expected >= 20 farms" }
if ([int]$outcomes -lt 40) { throw "FAIL: expected >= 40 plan_outcomes" }

Write-Host "==> minimal scenario run"
$payload = Get-Content -Raw "$PSScriptRoot\validate_demo_payload.json"
$resp = Invoke-RestMethod -Uri "http://localhost:8000/api/scenario/run" -Method Post -Body $payload -ContentType "application/json"
if (-not $resp.run_id) { throw "FAIL: scenario run missing run_id" }

Write-Host "PASS: demo stack is healthy"
