# AgentFarm Optimizer

Agentic AI for sustainable agri supply chains in India — predicts disruptions, optimizes routing and inventory, and advises smallholder farmers to reduce food waste and stockouts.

---

## Problem

India loses an estimated **30–40% of its fresh produce** between farm and market each year. Smallholder farmers and local distributors lack the forecasting, routing, and real-time advisory tools that large agribusinesses use. Weather disruptions (monsoon floods, heatwaves), demand volatility around festivals, and fragmented mandi logistics compound the problem — food spoils while other mandis go under-supplied.

**AgentFarm Optimizer** is a multi-agent AI system that autonomously senses disruptions, optimizes a plan across the supply chain, and explains it back to the farmer in plain language.

---

## Architecture

```
Client (Next.js)
  -> FastAPI Gateway
    -> Orchestrator (LangGraph — entry, conflict resolution, final packaging)
      -> +- Weather Agent --+  (parallel fan-out)
         |                  +--> Inventory Agent -> Logistics Agent -> Validator -> Plan Output
         +- Demand Agent ---+
    -> Postgres + Redis + Outcome Store

Advisor Agent (separate service, on-demand)
  -> Reads finished plans from Postgres
  -> Answers queries via /api/advisor/query
  -> Maintains per-session conversation buffer
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full system deep-dive.

---

## The Seven Agents

| Agent | Role | LLM? | Primary Tools |
|---|---|---|---|
| **Orchestrator** | Validates inputs, resolves conflicts, packages final plan | No | LangGraph state graph |
| **Weather** | Fetches 7-day forecasts per farm, classifies risk (normal / warning / severe) | No | OpenWeatherMap API, Redis cache |
| **Demand Forecast** | 7-day demand per mandi; adjusts for festivals, heatwaves, and past outcomes | Yes (temp 0) | Outcome Store, LLM |
| **Inventory** | Tracks produce at farms; predicts spoilage windows by crop + temperature | Yes (temp 0) | Postgres, temperature data |
| **Logistics** | Solves the VRP — truck to farm to mandi routing with capacity and time windows | No | Google OR-Tools, Maps API |
| **Validator** | Rule-based feasibility check (capacity, time windows, driver hours); triggers re-plan | No | Constraint checker |
| **Farmer Advisor** | Plain-language recommendations (English); interactive follow-up queries | Yes (temp 0.3) | LLM, Plan DB, Redis session |

---

## Tech Stack

- **Backend:** Python 3.11, FastAPI, LangGraph, Pydantic, SQLAlchemy 2.0 (async), Google OR-Tools
- **LLMs:** OpenAI `gpt-4o-mini` via OpenRouter (OpenRouter API key works directly)
- **Data:** PostgreSQL 16, Redis 7 (cache + session buffer)
- **Frontend:** Next.js 14, React 18, Tailwind CSS, React-Leaflet, Recharts
- **Infra:** Docker Compose (4 services: backend, frontend, postgres, redis)

---

## Demo (5 steps)

> Stack must be running first — see [Quick Start](#quick-start) below.

1. Open **http://localhost:3000/scenario**
2. Select **Monsoon Disruption** → click **RUN SCENARIO →**
3. Watch **7 AI agents** execute live (Weather → Demand → Inventory → Logistics → Validator → Orchestrator) — takes ~35 seconds
4. Click **View Dashboard →** → check KPI cards (56% waste reduction vs naive baseline), dark map with saffron truck routes
5. Switch tabs: **FARMER** (spoilage warnings + pickup times), **MANDI** (incoming supply vs demand bars), **TRANSPORT** (truck assignments + load bars) → go to **Advisor** → ask *"Which farm is highest risk today?"*

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- An **OpenRouter** or **OpenAI** API key — get one free at https://openrouter.ai

### 1 — Clone and configure environment

```bash
git clone <repo-url>
cd Unysis_AgentFarm

# Copy the example env file
cp .env.example .env
```

Open `.env` and fill in your keys:

```ini
# Required for LLM agents (Demand, Inventory, Advisor)
OPENAI_API_KEY=sk-or-v1-xxxxxxxxxxxx   # OpenRouter key OR OpenAI key

# Optional — improves accuracy, falls back gracefully without them
OPENWEATHER_API_KEY=                   # https://openweathermap.org/api
GOOGLE_MAPS_API_KEY=                   # https://console.cloud.google.com

# These are pre-set for Docker Compose — do not change unless running locally
DATABASE_URL=postgresql+asyncpg://agentfarm:agentfarm@postgres:5432/agentfarm
REDIS_URL=redis://redis:6379/0
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

> **No API key?** The demo still runs end-to-end. Weather and Logistics agents work without keys (Haversine fallback for distances). Demand and Inventory agents fall back to rule-based logic. The Advisor returns a curated static answer.

### 2 — Start all services

```bash
docker compose up -d --build
```

This builds and starts 4 containers:

| Container | Port | Role |
|---|---|---|
| `agentfarm_frontend` | 3000 | Next.js UI |
| `agentfarm_backend` | 8000 | FastAPI + LangGraph pipeline |
| `agentfarm_postgres` | 5432 | Plan storage + outcome history |
| `agentfarm_redis` | 6379 | Weather cache + advisor session buffer |

Wait ~30 seconds for the database to seed, then open **http://localhost:3000**.

### 3 — Verify everything is healthy

```bash
# All 4 containers should show "healthy" or "Up"
docker compose ps

# Backend health check
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# Swagger API docs
open http://localhost:8000/docs
```

### 4 — Stop the stack

```bash
docker compose down          # stop containers, keep data
docker compose down -v       # stop + wipe all volumes (fresh start)
```

---

## Manual Development Setup (without Docker)

### Backend

Requires Python 3.11+ and a running Postgres + Redis instance.

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (or create a .env in backend/)
export DATABASE_URL=postgresql+asyncpg://agentfarm:agentfarm@localhost:5432/agentfarm
export REDIS_URL=redis://localhost:6379/0
export OPENAI_API_KEY=sk-or-v1-xxxxxxxxxxxx
export OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Run with hot-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

Requires Node.js 18+.

```bash
cd frontend

# Install dependencies
npm install

# Point to the backend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api" > .env.local

# Start dev server with hot-reload
npm run dev
```

Frontend runs at **http://localhost:3000**.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Recommended | — | OpenAI or OpenRouter API key for LLM agents |
| `OPENAI_BASE_URL` | No | `https://api.openai.com/v1` | Override to `https://openrouter.ai/api/v1` for OpenRouter |
| `OPENWEATHER_API_KEY` | No | — | Live weather data; falls back to simulated events |
| `GOOGLE_MAPS_API_KEY` | No | — | Real distance matrix; falls back to Haversine formula |
| `DATABASE_URL` | Yes | see `.env.example` | PostgreSQL connection string (asyncpg driver) |
| `REDIS_URL` | Yes | see `.env.example` | Redis connection string |
| `VRP_TIME_LIMIT` | No | `30` | OR-Tools VRP solver time limit in seconds |
| `MAX_RETRIES` | No | `2` | Max plan retry loops before flagging for human review |
| `PLANNING_TEMP` | No | `0.0` | LLM temperature for Demand + Inventory agents |
| `ADVISOR_TEMP` | No | `0.3` | LLM temperature for Farmer Advisor (slightly warmer) |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/scenario/run` | Run a full scenario and receive the optimized plan + KPIs + agent traces |
| `GET` | `/api/run/{runId}` | Fetch a persisted plan plus summary metrics |
| `GET` | `/api/run/{runId}/traces` | Per-agent reasoning traces, tool calls, timings, token counts |
| `POST` | `/api/advisor/query` | Ask the Advisor a contextual question about a finished plan |
| `POST` | `/api/outcome/log` | Log real-world outcomes (feeds cross-run learning loop) |
| `GET` | `/health` | Liveness probe |

Full interactive docs: **http://localhost:8000/docs**

---

## Project Structure

```
Unysis_AgentFarm/
├── backend/
│   ├── agents/            # 7 agent modules (weather, demand, inventory,
│   │                      #   logistics, validator, orchestrator, advisor)
│   ├── memory/            # 3-tier memory: state (T1), outcome store (T2), sessions (T3)
│   ├── tools/             # weather_api, maps_api, vrp_solver, db
│   ├── models/            # Pydantic schemas + SQLAlchemy ORM models
│   ├── routes/            # FastAPI routers (scenario, run, advisor, outcome)
│   ├── config.py          # Pydantic settings (reads .env)
│   └── main.py            # FastAPI app entry point
├── frontend/
│   └── src/
│       ├── components/    # SimulationPanel, MapView, KPIGrid, AgentTrace,
│       │                  #   ScenarioForm, ChatInterface, Dashboard
│       ├── pages/         # scenario.js, dashboard.js, advisor.js, runs.js
│       ├── hooks/         # useScenario, useRuns, useAdvisor
│       ├── context/       # AppContext (run id, session id)
│       └── utils/         # api.js, demoFixtures.js, formatters.js
├── data/                  # Seed CSVs — farms, demand points, trucks, outcomes
├── docker-compose.yml
├── .env.example           # Copy to .env and fill in keys
├── ARCHITECTURE.md        # Full system design document
├── CONTRIBUTING.md        # Branch naming, commit conventions, review workflow
└── README.md
```

---

## Troubleshooting

**Backend container keeps restarting**
```bash
docker compose logs backend --tail 50
# Common causes: bad DATABASE_URL, missing .env, Python import error
```

**"Pipeline error — check that the backend is running at localhost:8000"**
```bash
docker compose ps          # backend should be Up (healthy)
curl http://localhost:8000/health
docker compose logs backend --tail 30
```

**LLM agents return rule-based answers only**
```bash
# Check the key is set
grep OPENAI_API_KEY .env

# Check the backend sees it
docker compose exec backend env | grep OPENAI
```

**Map tiles not loading**
The map uses OpenStreetMap tiles — requires internet access. The farm/mandi markers and routes still render correctly without tiles.

**Port already in use**
```bash
# Change ports in docker-compose.yml, e.g. "3001:3000" for the frontend
```

---

## Testing

```bash
# Backend unit + integration tests
cd backend
pytest --cov

# Frontend lint
cd frontend
npm run lint
```

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for branch naming, commit conventions, code style, and review workflow.

---

## License

MIT — see [LICENSE](./LICENSE).
