# AgentFarm Optimizer — Architecture

This document is the deep-dive on how the system is put together: the pipeline, the agents, the memory tiers, the data model, and the design decisions we made (including where we intentionally depart from the original PRD).

---

## System Diagram

```
+----------------------+          +--------------------------+
|  Client (Next.js)    | <------> |  FastAPI Gateway (:8000) |
+----------------------+          +-----------+--------------+
                                              |
                                              v
                               +------------------------------+
                               |  Orchestrator (LangGraph)    |
                               |  - entry: validate + load    |
                               |  - exit:  conflict + package |
                               +------+----------------+------+
                                      | fan-out        |
                          +-----------+                +-----------+
                          v                                        v
                   +-------------+                         +--------------+
                   | Weather     |                         | Demand       |
                   | Agent       |                         | Forecast     |
                   +------+------+                         +------+-------+
                          |                                       |
                          +------------------+--------------------+
                                             v
                                      +-------------+
                                      |  Merge      |
                                      +------+------+
                                             v
                                      +-------------+
                                      | Inventory   |
                                      +------+------+
                                             v
                                      +-------------+
                                      | Logistics   | <---+
                                      +------+------+     | relax + retry (<=2)
                                             v            |
                                      +-------------+     |
                                      | Validator   |-----+
                                      +------+------+
                                             v
                                      +-------------+
                                      | Orchestrator|
                                      | Exit        |
                                      +------+------+
                                             v
                                      +-------------+
                                      | Persist     |
                                      | (Postgres)  |
                                      +-------------+

   +----------------------------------+
   |  Advisor Agent (separate svc)    | <-- Redis session buffer + Plan DB
   |  POST /api/advisor/query          |
   +----------------------------------+
```

---

## Pipeline — Eight-Step Flow

1. User selects a scenario (Monsoon Disruption, Heat Wave, etc.) and supplies inputs (CSV upload or form).
2. Orchestrator validates inputs and loads context — including relevant past outcomes from the Outcome Store.
3. Weather and Demand agents run **in parallel** (fan-out — neither depends on the other).
4. Results merge back into shared state; Inventory agent calculates at-risk stock using spoilage windows.
5. Logistics agent builds an optimized route plan via OR-Tools VRP with capacity and time-window constraints.
6. Validator checks plan feasibility. On failure, Logistics re-solves with relaxed constraints (max 2 retries).
7. Orchestrator exits: resolves remaining conflicts, computes KPIs vs naive baseline, persists plan + run log.
8. Dashboard renders the map, routes, waste projections, and agent traces. The Advisor Agent is available separately for on-demand queries.

Target end-to-end time: **under 2 minutes** for 20 farms, 10 demand points, 10 trucks on standard cloud hardware.

---

## Agents in Detail

### Orchestrator (entry + exit bookends)

- **Inputs:** Raw `ScenarioRequest` (farms, demand points, trucks, scenario type, constraints).
- **Entry responsibilities:** generate `run_id`, validate schemas, pull past outcomes from Postgres, initialize `AgentFarmState`.
- **Exit responsibilities:** resolve any remaining inter-agent conflicts, compute KPI deltas vs baseline, write `Plan` + `RunLog` to Postgres.
- **LLM:** none (pure control flow).
- **Graph position:** START entry node and final pre-persist node.

### Weather Agent

- **Inputs:** list of farms with lat/lng.
- **Outputs:** `list[WeatherEvent]` and `weather_risk_summary: dict[farm_id -> risk_level]`.
- **Tools:** OpenWeatherMap API (cached in Redis, 1h TTL). Hardcoded synthetic fallback if API fails.
- **Risk classification:** `rain_mm > 50 = severe`, `> 20 = warning`, else `normal`. Temperature > 40C flags heat-wave risk.
- **LLM:** none.
- **Graph position:** parallel branch 1 (fan-out).

### Demand Forecast Agent

- **Inputs:** demand points, past outcomes (from Tier-2 memory), current calendar date, weather risk summary.
- **Outputs:** `demand_forecast: dict[demand_point_id -> 7-day list]`.
- **Tools:** CSV/DB for history, LLM (temp 0) for festival / heat-wave multiplier reasoning, Outcome Store for bias correction.
- **Graph position:** parallel branch 2 (fan-out).

### Inventory Agent

- **Inputs:** Farm produce state, weather risk summary, demand forecast.
- **Outputs:** `list[AtRiskStock]` — produce with narrow spoilage windows requiring priority dispatch.
- **Tools:** Postgres queries, temperature-adjusted shelf-life table. LLM call (temp 0) for prioritization ordering.
- **Graph position:** after Weather + Demand merge.

### Logistics Agent

- **Inputs:** At-risk stock, demand forecast, trucks, past route outcomes.
- **Outputs:** `RoutePlan` with truck-assigned stops and ETAs.
- **Tools:** Distance matrix (Google Maps or Haversine fallback x1.3), Redis cache, Google OR-Tools VRP (`PATH_CHEAPEST_ARC` + `GUIDED_LOCAL_SEARCH`, 30s time limit).
- **Retry behavior:** accepts a `relaxation_factor` when re-invoked by Validator.
- **LLM:** none.
- **Graph position:** after Inventory.

### Validator

- **Inputs:** `RoutePlan`, trucks, farms, demand points.
- **Outputs:** `ValidationResult` with pass/fail and violation list.
- **Checks:** vehicle capacity, time window compliance, availability windows, driver hours (14h max), at-risk-stock coverage.
- **LLM:** none (pure rule checks — faster and deterministic).
- **Graph position:** after Logistics; conditional edge back to Logistics on failure.

### Farmer Advisor (decoupled)

- **Inputs:** `run_id`, `session_id`, `user_question`.
- **Outputs:** `AdvisorResponse` with plain-language answer.
- **Tools:** LLM (temp 0.3, friendly tone), Plan DB lookup, Redis session buffer (last 10 messages, 24h TTL).
- **Graph position:** NOT in the main pipeline. Runs as a separate service behind `POST /api/advisor/query` so user chat latency never blocks scenario runs.

---

## Memory Architecture — Three Tiers

Implementation lives under `backend/memory/`: `state.py` (Tier 1), `outcome_store.py` (Tier 2), `session_buffer.py` (Tier 3). Postgres outcomes also backfill `demand_point_id` / `road_segment` from `data/sample_outcomes.csv` via `tools.db.backfill_outcome_dims_from_csv` after seed on startup.

### Tier 1 — Intra-Run (Short-Term)

A typed LangGraph state object (`AgentFarmState` TypedDict) passed between agents within a single run. All fields are Pydantic models — no free-form strings between agents.

```python
class AgentFarmState(TypedDict):
    # Input
    farms: list[Farm]
    demand_points: list[DemandPoint]
    trucks: list[Truck]
    scenario_type: str

    # Weather Agent output
    weather_events: list[WeatherEvent]
    weather_risk_summary: dict[str, str]

    # Demand Agent output
    demand_forecast: dict[str, list[float]]

    # Inventory Agent output
    at_risk_stock: list[AtRiskStock]

    # Logistics output
    route_plan: RoutePlan

    # Validator
    validation_result: ValidationResult
    retry_count: int

    # Orchestrator
    final_plan: Plan | None
    run_id: str
    agent_traces: list[AgentTrace]
```

### Tier 2 — Cross-Run (Learning Loop)

A `PlanOutcome` table in Postgres logs actual real-world results back to the system after plan execution:

```
PlanOutcome(
  run_id, plan_date,
  farm_id, demand_point_id,
  predicted_waste_kg, actual_waste_kg,
  predicted_delivery_time, actual_delivery_time,
  demand_predicted, demand_actual,
  notes
)
```

- **Demand Agent** on the next run pulls history: *"Last 3 Tuesdays, tomatoes to Mandi A underperformed forecast by 20%"* -> adjusts.
- **Logistics Agent** pulls route history: *"NH-48 during monsoon took 40% longer on average over last 5 runs"* -> adjusts travel time estimates.

For the hackathon this table is seeded with 30–50 synthetic historical rows so the feedback loop can be demonstrated from day one.

### Tier 3 — Conversational (Advisor Sessions)

Redis-backed per-session buffer:

```
advisor_session:{session_id} -> [
  { role: "user", content: "..." },
  { role: "assistant", content: "..." }
]
```

- TTL: 24 hours
- Max history: last 10 messages per session (keeps LLM context small)
- Each `/api/advisor/query` loads history + relevant plan and generates a contextual response.

---

## Data Model

Seven core entities:

| Entity | Purpose | Key fields |
|---|---|---|
| `Farm` | Source of produce | id, name, lat, lng, crop_type, acreage, typical_yield, harvest_window |
| `DemandPoint` | Mandi / retailer | id, name, lat, lng, type (apmc / private / retail), base_demand_per_day |
| `Truck` | Transport asset | id, capacity_kg, cost_per_km, availability_window |
| `WeatherEvent` | Forecast per farm-day | farm_id, date, rain_mm, temperature, risk_level |
| `Plan` | Optimized output | date, assignments (truck to route), expected_waste, cost |
| `RunLog` | Observability | run_id, timestamp, agents_involved, metrics_before, metrics_after, trace_link |
| `PlanOutcome` | Feedback ground truth | run_id, plan_date, farm_id, demand_point_id, predicted vs actual (waste, delivery, demand) |

---

## LangGraph Flow and Conditional Edges

```
START
  -> orchestrator_entry
  -> fan_out:
       +- weather_agent
       +- demand_agent
  -> merge
  -> inventory_agent
  -> logistics_agent
  -> validator
       (valid)   -> orchestrator_exit
       (fail, retries<2) -> logistics_agent (relax)
       (fail, retries>=2) -> orchestrator_exit (flag human review)
  -> orchestrator_exit
  -> persist
END
```

**Optimization edges:**

- If `weather_risk_summary` is `normal` for every farm, the Logistics node skips re-routing and uses cached routes from the last run.
- If no demand shift is detected vs last cached forecast, the Demand Agent is skipped entirely.

---

## Design Decisions and PRD Departures

The original PRD describes a strictly sequential Weather -> Demand -> Inventory -> Logistics -> Advisor pipeline with a heavy Orchestrator driving everything. We departed on four fronts:

1. **Weather + Demand run in parallel.** They have no data dependency on each other; fanning out saves wall-clock time and is idiomatic LangGraph.
2. **Validator added as a dedicated node.** The PRD mixed feasibility checks into the Logistics agent. Splitting them gives us a clean retry loop and a rule-based (deterministic, no-LLM) gate.
3. **Advisor decoupled from the pipeline.** Farmer Q&A should not add latency to every scenario run. The Advisor is its own service reading finished plans from Postgres.
4. **Outcome feedback loop added.** The PRD's "learn" phase had no implementation. `PlanOutcome` closes that loop — cross-run memory is now a first-class tier.

We also scoped the Orchestrator down to only (a) graph entry validation / context loading and (b) graph exit conflict resolution + plan packaging. LangGraph handles sequencing; we do not re-implement that in code.

---

## KPI Strategy

Every run computes KPIs against a **naive baseline** so improvement is measurable.

**Baseline:** nearest-mandi-first allocation, no weather awareness, greedy truck assignment, no optimization.

**Metrics:**
- Primary: `% reduction in predicted waste` vs baseline — **target 20–30%**
- Primary: `improvement in on-time deliveries` vs baseline
- Secondary: re-plans triggered per disruption, average run completion time, token usage per run

Without the baseline, "optimized" numbers are meaningless — this comparison is load-bearing for the demo.

---

## Why This Tech Stack

- **Python 3.11** — best ecosystem for ML, OR-Tools, and agent orchestration libraries.
- **FastAPI** — async-first, automatic OpenAPI docs, Pydantic integration, low ceremony.
- **LangGraph** — explicit graph with typed state (vs hidden prompt chaining); supports fan-out, conditional edges, and retry loops natively.
- **Google OR-Tools** — production-grade VRP solver with capacity, time windows, and a hard 30s time limit to avoid hangs. Free and well-maintained.
- **PostgreSQL** — relational store for plans/outcomes/logs; pgvector available if we add scenario embeddings later.
- **Redis** — sub-millisecond cache for weather and distance matrices; also hosts the Advisor session buffer with TTL semantics built in.
- **Next.js + Tailwind** — familiar stack, SSR available if needed, good map/chart ecosystem (React-Leaflet, Recharts).
- **Docker Compose** — one-command local bring-up; matches production deployment topology.

---

## Common Pitfalls We Explicitly Avoid

- Letting the LLM free-generate plans. Agents call tools and format results; they do not hallucinate routes.
- Storing raw LLM output as a plan. Everything is parsed into structured Pydantic models before persisting.
- Calling weather APIs per-agent. Shared Redis cache, 1h TTL.
- Running OR-Tools without a time limit. Hard cap at 30s; relaxation on retry.
- Shipping without a baseline. KPIs compare against naive allocation on every run.
