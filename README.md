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

## The Six Agents

| Agent | Role | Primary Tools |
|---|---|---|
| **Orchestrator** | Validates inputs, resolves inter-agent conflicts, packages final plan | LangGraph state graph |
| **Weather** | Fetches 7-day forecasts per farm, classifies risk (normal / warning / severe) | OpenWeatherMap API, Redis cache |
| **Demand Forecast** | 7-day demand per mandi; adjusts for festivals, heatwaves, and past outcomes | CSV/DB, LLM prompts, Outcome Store |
| **Inventory** | Tracks produce at farms and cold storage; predicts spoilage windows | Postgres, temperature data |
| **Logistics** | Solves the VRP — truck to farm to mandi routing with capacity and time windows | Google OR-Tools, Maps API |
| **Validator** | Rule-based feasibility check (capacity, time windows, driver hours); triggers re-plan | Constraint checker (no LLM) |
| **Farmer Advisor** | Plain-language recommendations (English/Hindi); interactive follow-up queries | LLM, Plan DB, Redis session buffer |

---

## Tech Stack

- **Backend:** Python 3.11, FastAPI, LangGraph, Pydantic, SQLAlchemy 2.0 (async), Google OR-Tools
- **LLMs:** GPT-4.1 mini (planning, temp 0) and Groq-hosted models (advisor, temp 0.3)
- **Data:** PostgreSQL 16 (pgvector optional), Redis 7 (cache + session buffer)
- **Frontend:** Next.js 14, TypeScript, Tailwind, React-Leaflet, Recharts
- **Infra:** Docker Compose, GitHub Actions CI/CD

---

## Quick Start

Requires Docker and Docker Compose.

```bash
cp .env.example .env
# edit .env and add your OPENWEATHER_API_KEY and OPENAI_API_KEY (others optional)
docker compose up -d
open http://localhost:3000
```

The backend will be reachable at `http://localhost:8000` (Swagger docs at `/docs`).

---

## Manual Development Setup

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/scenario/run` | Run a full scenario (Monsoon, Heatwave, etc.) and receive the optimized plan + KPIs |
| GET | `/api/run/{runId}` | Fetch a persisted plan plus summary metrics |
| GET | `/api/run/{runId}/traces` | Per-agent reasoning traces, tool calls, timings, and token counts |
| POST | `/api/advisor/query` | Ask the Advisor Agent a question about a finished plan (conversational, session-keyed) |
| POST | `/api/outcome/log` | Log actual real-world outcomes of an executed plan (feeds the cross-run learning loop) |
| GET | `/health` | Liveness probe |

---

## Project Structure

```
agentfarm/
├── backend/               # FastAPI + LangGraph agent pipeline
│   ├── agents/            # 7 agent modules
│   ├── memory/            # 3-tier memory (state, outcomes, sessions)
│   ├── tools/             # Weather, maps, VRP solver, DB
│   ├── models/            # Pydantic + SQLAlchemy
│   ├── routes/            # FastAPI routers
│   └── main.py
├── frontend/              # Next.js dashboard
│   └── src/
│       ├── components/    # ScenarioForm, MapView, KPIDashboard, AgentTraces, AdvisorChat
│       └── lib/
├── data/                  # Seed CSVs (farms, demand, trucks, historical outcomes)
├── .github/workflows/     # CI: test, lint, deploy
├── docker-compose.yml
├── ARCHITECTURE.md
├── CONTRIBUTING.md
└── README.md
```

---

## Testing

```bash
# Backend
cd backend && pytest --cov

# Frontend
cd frontend && npm test
```

Targets: VRP solver, validator, demand agent, metrics; plus a full-pipeline integration test with seed data.

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for branch naming, commit conventions, code style, and review workflow.

---

## License

MIT — see [LICENSE](./LICENSE).
