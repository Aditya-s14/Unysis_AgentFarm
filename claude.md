# CLAUDE.md — AgentFarm Optimizer

## Project Identity

**AgentFarm Optimizer** — Agentic AI for sustainable agri supply chains in India.
Multi-agent system that autonomously predicts disruptions, optimizes inventory/routing, and advises smallholder farmers and local distributors to reduce food waste and stockouts.

---

## Architecture Overview

### Improved Pipeline (Parallel + Validated + Decoupled Advisor)

```
Client (React/Next.js or Streamlit)
  → FastAPI Gateway
    → Orchestrator (LangGraph — graph entry, conflict resolution, final packaging)
      → ┌─ Weather Agent ──┐  (parallel fan-out)
        │                  ├──→ Inventory Agent → Logistics Agent → Validator → Plan Output
        └─ Demand Agent ───┘
    → Postgres + Redis + Outcome Store

Advisor Agent (separate service, on-demand)
  → Reads finished plans from Postgres
  → Answers queries via /api/advisor/query
  → Maintains per-session conversation buffer
```

### Why This Differs From the PRD

The original PRD describes a strictly sequential pipeline: Weather → Demand → Inventory → Logistics → Advisor, all controlled by a heavy Orchestrator. The improved architecture makes these changes:

1. **Weather + Demand run in parallel** — they don't depend on each other, so fan-out saves time
2. **Validator node added** — checks plan feasibility (capacity limits, time window violations) before packaging
3. **Advisor Agent decoupled** — removed from the main pipeline; runs as a separate query service so it doesn't add latency to every run
4. **Orchestrator scoped down** — only handles conflict resolution and final plan validation, not agent sequencing (LangGraph handles that)
5. **Outcome feedback loop added** — past plan results feed back into future runs (see Memory Architecture below)

### Agent Roles (7 nodes in graph)

| Agent / Node | Responsibility | Tools | Position in Graph |
|-------------|---------------|-------|-------------------|
| **Orchestrator** | Validate inputs, resolve inter-agent conflicts, package final plan | LangGraph state | Entry + exit node |
| **Weather** | Fetch forecasts per farm, classify risk (normal/warning/severe) | Weather API, Redis cache | Parallel branch 1 |
| **Demand Forecast** | 7-day demand forecast, adjust for festivals/heatwaves | CSV/DB, LLM prompts, Outcome Store | Parallel branch 2 |
| **Inventory** | Track produce at farms/cold storage, predict spoilage risk | Postgres, temperature data | After Weather + Demand merge |
| **Logistics** | Solve VRP — truck→farm→mandi routing with constraints | OR-Tools, Maps API | After Inventory |
| **Validator** | Check plan feasibility — capacity, time windows, route validity | Constraint checker (no LLM) | After Logistics |
| **Farmer Advisor** | Plain-language recommendations (English/Hindi), interactive queries | LLM, Plan DB, session buffer | **Separate service** (not in pipeline) |

### LangGraph Flow Definition

```
START
  → orchestrator_entry (validate inputs, load context)
  → fan_out:
      ├── weather_agent (fetch forecasts, classify risk)
      └── demand_agent (forecast demand, pull past outcomes)
  → merge (combine weather + demand into shared state)
  → inventory_agent (spoilage risk, at-risk stock)
  → logistics_agent (VRP solve, route plan)
  → validator (constraint check — if FAIL → loop back to logistics with adjusted constraints)
  → orchestrator_exit (conflict resolution, final plan packaging)
  → persist (write Plan + RunLog to Postgres)
END
```

Conditional edges:
- If weather risk_level = "normal" for all farms → skip re-routing logic in Logistics, use cached routes
- If Validator fails → re-invoke Logistics with relaxed constraints (max 2 retries, then flag for human review)
- If no demand change detected → skip Demand Agent entirely (use last cached forecast)

---

## Memory Architecture

The PRD's "sense-reason-act-learn" cycle is missing the "learn" implementation. Here's the three-tier memory system:

### Tier 1: Intra-Run Memory (Short-Term)

**What:** LangGraph shared state (TypedDict) that passes between agents within a single scenario run.

**How:** Each agent reads from and writes to typed fields in the state object. No free-form strings — everything is a Pydantic model.

```python
class AgentFarmState(TypedDict):
    # Input
    farms: list[Farm]
    demand_points: list[DemandPoint]
    trucks: list[Truck]
    scenario_type: str

    # Weather Agent output
    weather_events: list[WeatherEvent]
    weather_risk_summary: dict[str, str]  # farm_id → risk_level

    # Demand Agent output
    demand_forecast: dict[str, list[float]]  # demand_point_id → 7-day forecast

    # Inventory Agent output
    at_risk_stock: list[AtRiskStock]  # produce with spoilage windows

    # Logistics Agent output
    route_plan: RoutePlan
    
    # Validator output
    validation_result: ValidationResult
    retry_count: int

    # Orchestrator
    final_plan: Plan
    run_id: str
```

### Tier 2: Cross-Run Memory (Learning from Outcomes)

**What:** After a plan executes in the real world, actual outcomes get logged back — did produce sell? Did trucks arrive on time? How much waste occurred?

**How:** A new `PlanOutcome` entity in Postgres:

```
PlanOutcome:
  run_id, plan_date,
  farm_id, demand_point_id,
  predicted_waste_kg, actual_waste_kg,
  predicted_delivery_time, actual_delivery_time,
  demand_predicted, demand_actual,
  notes
```

At the start of each new run, the Demand Agent and Logistics Agent pull relevant past outcomes:
- Demand Agent: "Last 3 times we sent tomatoes to Mandi A on a Tuesday, actual demand was 20% below prediction" → adjusts forecast
- Logistics Agent: "Route via NH-48 during monsoon took 40% longer than estimated last 5 runs" → adjusts travel time estimates

For the hackathon, seed this table with synthetic historical outcomes to demonstrate the feedback loop working.

### Tier 3: Conversational Memory (Advisor Agent)

**What:** The Advisor Agent maintains conversation context so farmers can ask follow-up questions.

**How:** A simple session-keyed buffer stored in Redis:

```
advisor_session:{session_id} → [
  { role: "user", content: "What should Farm 7 do tomorrow?" },
  { role: "assistant", content: "Harvest early morning, send to Mandi B..." },
  { role: "user", content: "What about the day after?" }
]
```

- TTL: 24 hours (conversations don't need to persist longer)
- Max history: last 10 messages per session (keep LLM context small)
- Each query to `/api/advisor/query` includes session_id; the Advisor loads history + the relevant plan and generates a contextual response

---

## Tech Stack

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Agent Orchestration:** LangGraph (primary), CrewAI/AutoGen as alternatives
- **LLMs:** GPT-4.1 mini/small or Groq-hosted open-weight models (cost control)
- **Optimization:** Google OR-Tools for VRP with capacities and time windows
- **Weather:** OpenWeatherMap API (India coverage)
- **Maps/Routing:** Google Maps Directions API or OSRM (open-source)

### Data Layer
- **Database:** PostgreSQL (primary relational store)
- **Vector Search:** pgvector extension (optional — past scenario embeddings)
- **Cache:** Redis (weather data, distance matrices — short TTL)

### Frontend
- **Framework:** React / Next.js
- **Maps:** React-Leaflet or Google Maps React
- **Charts:** Recharts or Chart.js
- **Deployment:** Vercel or Netlify

### Infrastructure
- **Containers:** Docker (backend + orchestrator)
- **Backend Hosting:** Render / Fly.io / EC2
- **CI:** GitHub Actions (tests + deploy)
- **Observability:** LangSmith or lightweight OSS tracing

---

## Data Model

### Core Entities
- **Farm:** id, name, location (lat/lng), crop_type, acreage, typical_yield, harvest_window
- **DemandPoint:** id, name, location, type (mandi | retailer), base_demand_per_day
- **Truck:** id, capacity_kg, cost_per_km, availability_window
- **WeatherEvent:** farm_id, date, rain_mm, temperature, risk_level
- **Plan:** date, assignments (truck → route → pick/drop stops), expected_waste, cost
- **RunLog:** run_id, timestamp, agents_involved, metrics_before, metrics_after, trace_link
- **PlanOutcome:** run_id, plan_date, farm_id, demand_point_id, predicted_waste_kg, actual_waste_kg, predicted_delivery_time, actual_delivery_time, demand_predicted, demand_actual, notes

### Scale Requirements
- Minimum: 20 farms, 10 demand points, 10 trucks per run
- Full pipeline must complete in < 2 minutes on standard cloud hardware
- Agent traces stored and retrievable by run_id

---

## API Endpoints

```
POST /api/scenario/run
  Body: { farms, demandPoints, trucks, constraints, scenarioType }
  Response: { plan, KPIs, runId }

GET  /api/run/{runId}
  Response: { plan, traces_summary, metrics }

GET  /api/run/{runId}/traces
  Response: { agent_steps, tool_calls, timings }

POST /api/advisor/query
  Body: { runId, sessionId, userQuestion }
  Response: { answer (natural language referencing plan), sessionId }
  Note: sessionId enables conversational memory — follow-up questions retain context

POST /api/outcome/log
  Body: { runId, outcomes[] }
  Response: { logged_count }
  Note: logs actual results after plan execution for cross-run learning
```

---

## Scenario Templates

1. **Monsoon Disruption** — Heavy rain predicted → adjust harvest timing and reroute trucks
2. **Heat Wave** — Increased spoilage risk → prioritize quick routing and cold storage allocation

### Agent Workflow Per Scenario
1. User selects scenario + inputs data (CSV upload or manual)
2. Orchestrator validates inputs and loads context (including past outcomes from Outcome Store)
3. Weather + Demand agents run **in parallel** (fan-out)
4. Results merge; Inventory agent calculates at-risk stock
5. Logistics agent builds optimized route plan via OR-Tools
6. Validator checks plan feasibility — if constraints violated, Logistics re-solves (max 2 retries)
7. Orchestrator packages final plan, persists to Postgres
8. Dashboard renders map, routes, waste projections, agent traces
9. Advisor Agent available separately for on-demand queries against the finished plan

---

## KPIs & Evaluation

### Primary Metrics
- **% reduction in predicted waste** vs naive baseline (target: 20–30%)
- **Improvement in on-time deliveries** vs baseline

### Secondary Metrics
- Number of re-plans triggered per disruption scenario
- Average run completion time
- Token usage per run

### Baseline Strategy (for comparison)
- Nearest-mandi-first allocation, no weather awareness, no optimization

---

## Project Structure (Recommended)

```
agentfarm/
├── backend/
│   ├── main.py                  # FastAPI app entry
│   ├── config.py                # Env vars, API keys, model config
│   ├── agents/
│   │   ├── orchestrator.py      # LangGraph flow definition (graph, edges, fan-out)
│   │   ├── weather_agent.py
│   │   ├── demand_agent.py
│   │   ├── inventory_agent.py
│   │   ├── logistics_agent.py
│   │   ├── validator.py         # Plan feasibility checker (no LLM)
│   │   └── advisor_agent.py     # Decoupled query service (not in main pipeline)
│   ├── memory/
│   │   ├── state.py             # AgentFarmState TypedDict (Tier 1 — intra-run)
│   │   ├── outcome_store.py     # PlanOutcome read/write (Tier 2 — cross-run learning)
│   │   └── session_buffer.py    # Redis conversation buffer (Tier 3 — advisor sessions)
│   ├── tools/
│   │   ├── weather_api.py       # OpenWeatherMap client
│   │   ├── maps_api.py          # Distance matrix / routing
│   │   ├── vrp_solver.py        # OR-Tools VRP wrapper
│   │   └── db.py                # Postgres queries
│   ├── models/
│   │   ├── schemas.py           # Pydantic models for all entities
│   │   └── db_models.py         # SQLAlchemy / raw SQL models
│   ├── routes/
│   │   ├── scenario.py          # /api/scenario/run
│   │   ├── runs.py              # /api/run/{runId}
│   │   └── advisor.py           # /api/advisor/query (separate from pipeline)
│   └── utils/
│       ├── logging.py           # Per-agent structured logging
│       └── metrics.py           # KPI computation helpers
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ScenarioForm.tsx
│   │   │   ├── MapView.tsx      # Farm/mandi/route visualization
│   │   │   ├── AgentTraces.tsx  # Reasoning trace viewer
│   │   │   ├── KPIDashboard.tsx # Waste/delivery charts
│   │   │   └── AdvisorChat.tsx  # Query the advisor agent
│   │   ├── pages/
│   │   └── lib/
│   │       └── api.ts           # API client
│   └── package.json
├── data/
│   ├── sample_farms.csv
│   ├── sample_demand.csv
│   ├── sample_trucks.csv
│   └── sample_outcomes.csv      # Synthetic historical outcomes for feedback loop demo
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
├── claude.md                    # ← This file
└── README.md
```

---

## Development Guidelines

### Code Style
- Python: follow PEP 8, use type hints everywhere, Pydantic for all data models
- TypeScript: strict mode, functional components with hooks
- All agent functions must return structured output (Pydantic models, not raw strings)

### Agent Development Rules
1. **Each agent is a self-contained module** — owns its tools, prompts, and output schema
2. **Agents communicate via structured state** — no free-form string passing between agents
3. **Every agent step is logged** — run_id, agent_name, step, tool_called, duration, token_count
4. **LLM calls must have temperature=0** for reproducibility in planning agents (Advisor can use 0.3)
5. **Tool calls are idempotent** — weather fetch, distance lookup, etc. should be cacheable
6. **Keep LLM token usage minimal** — use structured prompts, avoid verbose system messages

### LangGraph Conventions
- Graph state is a TypedDict with clear fields per agent's contribution
- Use conditional edges for disruption handling (e.g., skip logistics replan if weather is normal)
- Orchestrator node runs first and last (bookend pattern)

### Testing
- Unit tests for each agent's core logic (mock external APIs)
- Integration test: run full scenario pipeline with sample data, assert KPI improvements
- Trace validation: ensure every run produces retrievable traces

### Environment Variables
```
OPENAI_API_KEY=
OPENWEATHER_API_KEY=
GOOGLE_MAPS_API_KEY=        # or OSRM_BASE_URL for open-source
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
LANGSMITH_API_KEY=           # optional, for tracing
MODEL_NAME=gpt-4.1-mini     # or groq model identifier
```

---

## Execution Plan (3-Day Hackathon)

### Day 1: Foundation
- [ ] Finalize DB schema in Postgres (all 6 entities)
- [ ] Implement Weather Agent + OpenWeatherMap integration
- [ ] Implement Demand Forecast Agent (CSV ingest + seasonality)
- [ ] Wire both into LangGraph orchestrator skeleton
- [ ] Seed sample data (farms, demand points, trucks)

### Day 2: Core Pipeline
- [ ] Implement Inventory Agent (spoilage risk calculation)
- [ ] Implement Logistics Agent + OR-Tools VRP solver
- [ ] Build `POST /api/scenario/run` endpoint with full pipeline
- [ ] Add DB persistence for plans and run logs
- [ ] Test end-to-end with Monsoon Disruption scenario

### Day 3: Dashboard & Polish
- [ ] Implement Farmer Advisor Agent (plain-language output)
- [ ] Build React/Next.js dashboard (scenario form, map, charts, traces)
- [ ] Add KPI computation (waste reduction %, on-time improvement %)
- [ ] Logging, error handling, demo narrative
- [ ] Record demo video / prepare live walkthrough

---

## India-Specific Considerations

- Support regional units: bigha, acre, quintal alongside metric
- Crop calendars: Kharif (Jun–Oct), Rabi (Nov–Mar), Zaid (Mar–Jun)
- Festival demand spikes: Diwali, Pongal, Onam, Eid — model as demand multipliers
- Connectivity: design advisor responses to be SMS-length for low-bandwidth scenarios
- Language: English primary, Hindi stretch goal for Advisor Agent output
- Mandi types: APMC mandis, private mandis, direct retail — different demand profiles

---

## Common Pitfalls to Avoid

1. **Don't over-engineer the LLM layer** — agents should mostly call tools and format results, not free-generate plans
2. **Don't skip the baseline** — KPI improvements are meaningless without a naive comparison
3. **Don't ignore OR-Tools constraints** — always set time limits on VRP solver (30s max) to avoid hanging
4. **Don't store raw LLM outputs as plans** — parse into structured Plan objects before persisting
5. **Don't call weather API per-agent** — cache in Redis with 1-hour TTL, share across agents
6. **Don't hardcode coordinates** — use the sample CSV data model, keep location data external

---

## Demo Narrative (Suggested Flow)

1. **Setup:** Show 20 farms across Karnataka/Maharashtra, 10 mandis, 10 trucks on map
2. **Baseline Run:** Run without optimization — show waste % and delivery failures
3. **Trigger Monsoon Scenario:** Heavy rain alert for 5 farms
4. **Agent Reasoning:** Walk through Weather → Demand → Inventory → Logistics chain
5. **Optimized Plan:** Show rerouted trucks, shifted harvest, reduced waste on dashboard
6. **KPI Comparison:** Side-by-side waste reduction chart (baseline vs optimized)
7. **Advisor Query:** Ask "What should Farm #7 do tomorrow?" — get plain-language answer
8. **Trace View:** Show agent reasoning steps for transparency
