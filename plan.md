# AgentFarm Optimizer — Implementation Plan

## Context
Greenfield hackathon project (3 days). No code exists yet — only `claude.md` (spec) and `Project_Explaination.docx`. Goal: build a multi-agent AI system for Indian agri supply chain optimization with a working demo showing 20-30% waste reduction.

---

## Phase 0: Project Scaffolding (Day 1, ~2h)
- [ ] **0.1** Git init, `.gitignore`
- [ ] **0.2** `.env.example` with all API keys
- [ ] **0.3** `backend/config.py` — Pydantic Settings (API keys, model config, `vrp_time_limit=30`, `max_retries=2`, `planning_temp=0`, `advisor_temp=0.3`)
- [ ] **0.4** `requirements.txt` — fastapi, uvicorn, langgraph, openai, ortools, sqlalchemy, asyncpg, redis, pydantic, httpx
- [ ] **0.5** `backend/main.py` — FastAPI app, CORS, lifespan (DB+Redis connect), `GET /health`
- [ ] **0.6** `docker-compose.yml` — backend, frontend, postgres, redis
- [ ] **0.7** `Dockerfile` for backend
- [ ] **0.8** Frontend skeleton — `npx create-next-app` with TypeScript + Tailwind
- [ ] **0.9** `frontend/src/lib/api.ts` — typed API client stubs

**Done when:** `docker compose up` → health check returns 200, frontend renders

---

## Phase 1: Data Layer (Day 1, ~2h)
- [ ] **1.1** `models/schemas.py` — All Pydantic models:
  - Input: `Farm`, `DemandPoint`, `Truck`
  - Agent outputs: `WeatherEvent`, `DemandForecast`, `AtRiskStock`, `RouteStop`, `Route`, `RoutePlan`, `ValidationResult`
  - Plan: `Plan`, `RunLog`, `PlanOutcome`
  - API: `ScenarioRequest`, `ScenarioResponse`, `AdvisorRequest`, `AdvisorResponse`
- [ ] **1.2** `models/db_models.py` — SQLAlchemy 2.0 tables: farms, demand_points, trucks, plans, run_logs, plan_outcomes
- [ ] **1.3** `tools/db.py` — async session, `init_db()`, `seed_from_csv()`, CRUD helpers
- [ ] **1.4** Seed CSVs in `data/`:
  - `sample_farms.csv` — 20 farms (Karnataka + Maharashtra), 4 crop types (tomato, onion, banana, mango)
  - `sample_demand.csv` — 10 demand points (6 APMC, 3 private, 1 retail)
  - `sample_trucks.csv` — 10 trucks (1-ton, 3-ton, 5-ton mix)
  - `sample_outcomes.csv` — 30-50 synthetic historical outcomes for learning loop demo
- [ ] **1.5** Seed script — auto-load CSVs on startup if tables empty

**Done when:** Tables created, seed data queryable

---

## Phase 2: Memory Architecture (Day 1, ~1h)
- [ ] **2.1** `memory/state.py` — `AgentFarmState(TypedDict)` with all agent I/O fields + `agent_traces` list
- [ ] **2.2** `memory/outcome_store.py` — `log_outcomes()`, `get_demand_history()`, `get_route_history()`
- [ ] **2.3** `memory/session_buffer.py` — Redis-backed: `push_message()`, `get_history()`, `clear_session()` (TTL 24h, max 10 msgs)

**Done when:** State instantiable, outcomes read/write to Postgres, sessions read/write to Redis

---

## Phase 3: Tools Layer (Day 1, ~2h)
- [ ] **3.1** `tools/weather_api.py` — OpenWeatherMap client with Redis cache (1h TTL), risk classification (rain>50mm=severe, >20mm=warning), **hardcoded fallback** if API unavailable
- [ ] **3.2** `tools/maps_api.py` — Distance matrix with Redis cache, **Haversine fallback** (×1.3 road factor) to avoid Google Maps costs
- [ ] **3.3** `tools/vrp_solver.py` — OR-Tools CVRPTW: capacity constraints, time windows, `PATH_CHEAPEST_ARC` + `GUIDED_LOCAL_SEARCH`, 30s time limit, `relaxation_factor` param for validator retries

**Done when:** Each tool callable independently, VRP solves a 5-farm test case in <30s

---

## Phase 4: Agents (Day 1 evening + Day 2 morning, ~7h)
Each agent: `async def run(state: AgentFarmState) -> AgentFarmState`, appends trace entry.

- [ ] **4.1** Weather Agent — fetch forecasts per farm, classify risk, no LLM
- [ ] **4.2** Demand Agent — 7-day forecast with festival multipliers, weather adjustments, outcome-based correction, **LLM call** (temp=0)
- [ ] **4.3** Inventory Agent — spoilage calculation (crop shelf life × temp factor × days since harvest), **LLM call** for prioritization (temp=0)
- [ ] **4.4** Logistics Agent — build distance matrix, pull route history, call VRP solver, handle relaxation on retry, no LLM
- [ ] **4.5** Validator — rule-based checks: capacity, time windows, availability, driver hours (14h max), at-risk coverage. No LLM
- [ ] **4.6** Orchestrator Entry — generate run_id, validate inputs, load past context, init state
- [ ] **4.7** Orchestrator Exit — resolve conflicts, compute KPIs, persist plan + run_log to DB
- [ ] **4.8** Advisor Agent — **separate service**, loads plan from DB + conversation history from Redis, **LLM call** (temp=0.3), plain-language output

**Done when:** Each agent produces correct output from manually constructed state

---

## Phase 5: LangGraph Wiring (Day 2 afternoon, ~3h)
- [ ] **5.1** Graph definition in `orchestrator.py` — `StateGraph(AgentFarmState)` with 8 nodes
- [ ] **5.2** Edge wiring:
  - `START → orchestrator_entry → [weather, demand]` (parallel fan-out)
  - `[weather, demand] → merge → inventory → logistics → validator`
  - Validator conditional: valid → orchestrator_exit, invalid + retries<2 → logistics, invalid + retries>=2 → orchestrator_exit (flag human review)
  - `orchestrator_exit → persist → END`
- [ ] **5.3** Conditional skip edges — skip demand if cached, use cached routes if all weather normal
- [ ] **5.4** `run_scenario()` function — builds initial state, invokes graph, returns response

**Done when:** Full pipeline completes for monsoon scenario with 20 farms in <2 min

---

## Phase 6: API Endpoints (Day 2 evening, ~2h)
- [ ] **6.1** `routes/scenario.py` — `POST /api/scenario/run`
- [ ] **6.2** `routes/runs.py` — `GET /api/run/{runId}`, `GET /api/run/{runId}/traces`
- [ ] **6.3** `routes/advisor.py` — `POST /api/advisor/query`, `POST /api/outcome/log`
- [ ] **6.4** Router registration in `main.py`, global error handler

**Done when:** All 5 endpoints callable via curl, return correct data

---

## Phase 7: Baseline & KPI Computation (Day 2, ~1h)
- [ ] **7.1** `utils/metrics.py` — `compute_naive_baseline()` (nearest-mandi, no weather, greedy trucks)
- [ ] **7.2** `compute_kpi_delta()` — waste_reduction_%, cost_savings_%, on_time_improvement_%
- [ ] **7.3** Integrate into orchestrator_exit — every run returns baseline vs optimized KPIs

**Done when:** Monsoon scenario shows measurable waste reduction (target 20-30%)

---

## Phase 8: Frontend (Day 3, ~6h)
- [ ] **8.1** Layout — nav bar, two-column dashboard
- [ ] **8.2** `ScenarioForm.tsx` — scenario type dropdown, "Run Scenario" button, loading state
- [ ] **8.3** `MapView.tsx` — React-Leaflet, farm markers (green/red by risk), mandi markers (blue), truck route polylines, clickable popups
- [ ] **8.4** `KPIDashboard.tsx` — 4 stat cards, bar chart (baseline vs optimized waste), 7-day demand line chart
- [ ] **8.5** `AgentTraces.tsx` — vertical timeline, collapsible agent cards with duration/tools/tokens
- [ ] **8.6** `AdvisorChat.tsx` — chat bubbles, session management, suggestion buttons
- [ ] **8.7** `api.ts` — implement all API client functions with proper types

**Done when:** Full demo flow: select scenario → run → map + KPIs + traces → advisor chat

---

## Phase 9: Testing & Demo Prep (Day 3, ~4h)
- [ ] **9.1** Unit tests — VRP solver, validator, demand agent, metrics
- [ ] **9.2** Integration test — full pipeline end-to-end with seed data
- [ ] **9.3** Error resilience — weather fallback, VRP timeout, validator retry cap, advisor empty plan
- [ ] **9.4** Demo data tuning — ensure monsoon scenario shows dramatic rerouting, baseline ~35-40% waste
- [ ] **9.5** Demo script rehearsal (8-step narrative from CLAUDE.md)
- [ ] **9.6** Final cleanup — README, `.env.example` docs, `docker compose up` as single command

---

## Dependency Graph
```
Phase 0 (Scaffold)
  ↓
Phase 1 (Data) ──→ Phase 3 (Tools)
  ↓                    ↓
Phase 2 (Memory) ──→ Phase 4 (Agents)
                       ↓
                 Phase 5 (LangGraph)
                    ↓         ↓
              Phase 6 (API)  Phase 7 (KPIs)
                    ↓         ↓
                 Phase 8 (Frontend)
                       ↓
                 Phase 9 (Test+Demo)
```

## Risk Mitigation
| Risk | Mitigation |
|------|-----------|
| Weather API down | Hardcoded synthetic fallback |
| Google Maps cost | Haversine fallback, no dependency |
| VRP infeasible | Relaxation on retry, greedy degradation |
| LLM latency | Cache, short prompts, GPT-4.1 mini |
| Frontend not ready | Backend demo-able via Swagger UI |
| KPIs below target | Tune seed data (synthetic, controllable) |

## Critical Files
- `backend/agents/orchestrator.py` — graph definition, entry/exit, `run_scenario()`
- `backend/models/schemas.py` — all Pydantic types (everything depends on this)
- `backend/tools/vrp_solver.py` — core optimization, most complex single file
- `backend/memory/state.py` — `AgentFarmState` shared contract
- `backend/main.py` — FastAPI entry, lifespan, routers

## Team Assignment (5 members)
| Member | Primary Ownership | Phases |
|--------|------------------|--------|
| **Member 1** | Scaffolding + Infrastructure | Phase 0, Docker, CI/CD |
| **Member 2** | Data Layer + Memory | Phase 1, Phase 2 |
| **Member 3** | Tools + Agents (Weather, Demand, Inventory) | Phase 3, Phase 4.1-4.3 |
| **Member 4** | Agents (Logistics, Validator, Orchestrator) + LangGraph | Phase 4.4-4.7, Phase 5 |
| **Member 5** | Frontend + Advisor Agent | Phase 4.8, Phase 8 |
| **All** | API, KPIs, Testing, Demo | Phase 6, 7, 9 |
