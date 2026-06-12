# AgentFarm Optimizer

Agentic AI for sustainable agri supply chains in India — predicts disruptions, optimizes routing and inventory, and advises smallholder farmers to reduce food waste and stockouts.

---

## Problem

India loses an estimated **30–40% of its fresh produce** between farm and market each year. Smallholder farmers and local distributors lack the forecasting, routing, and real-time advisory tools that large agribusinesses use. Weather disruptions (monsoon floods, heatwaves), demand volatility around festivals, and fragmented mandi logistics compound the problem — food spoils while other mandis go under-supplied.

Many farmers and truck drivers operate **without reliable internet** (feature phones, no data plan). A plan computed in a connected control room is useless in the field unless pickup instructions reach people on **cellular SMS and optional voice** — the last-mile channel when dashboards and apps are unreachable.

**AgentFarm Optimizer** is a multi-agent AI system that autonomously senses disruptions, optimizes a plan across the supply chain, explains it back to the farmer in plain language, and — after **FPO approval** — dispatches pickup alerts to farmers and route assignments to drivers.

---

## Architecture

```mermaid
flowchart TB
  subgraph client["Client"]
    UI["Next.js UI"]
  end

  subgraph api["API layer"]
    GW["FastAPI Gateway :8000"]
  end

  subgraph pipeline["LangGraph pipeline"]
    ENTRY["Orchestrator entry"]
    W["Weather agent"]
    D["Demand agent"]
    MERGE["Merge"]
    INV["Inventory agent"]
    LOG["Logistics agent"]
    VAL["Validator"]
    RETRY["Retry prep"]
    EXIT["Orchestrator exit"]
    PERSIST["Persist KPIs"]
    ENTRY --> W
    W --> MERGE
    MERGE --> D
    D --> INV
    INV --> LOG
    LOG --> VAL
    VAL -->|valid| EXIT
    VAL -->|invalid, retries left| RETRY
    RETRY --> LOG
    VAL -->|invalid, max retries| EXIT
    EXIT --> PERSIST
  end

  subgraph data["Data & cache"]
    PG[("PostgreSQL")]
    RD[("Redis")]
  end

  subgraph advisor_svc["Advisor (on-demand)"]
    ADV["Farmer Advisor API"]
  end

  subgraph notify["Last-mile comms (offline field)"]
    FPO["FPO approval gateway"]
    SMS["SMS / voice → farmers + drivers"]
    NLOG[("notification_logs")]
  end

  UI --> GW
  GW --> ENTRY
  PERSIST --> PG
  W --> RD
  LOG --> RD
  GW --> ADV
  ADV --> PG
  ADV --> RD
  PERSIST --> FPO
  FPO -->|Approve & Notify| SMS
  SMS --> NLOG
  NLOG --> PG
```

**How it works:** The orchestrator validates inputs and loads run context. **Weather runs first**, then Demand (so API fallbacks can switch the effective scenario to `live_weather` before forecasting). Inventory and Logistics build an optimized plan. The Validator applies rule-based feasibility checks; on failure, Logistics re-solves with relaxed demand (up to two retries). The orchestrator exit packages the plan, KPIs vs a naive baseline, a **weather snapshot** (per-farm OpenWeather readings in Postgres + Redis), and a **scenario snapshot** (needed to rebuild notification context). When `NOTIFY_ENABLED=true`, farmer and driver alerts are **held** until the FPO officer clicks **Approve & Notify** on the dashboard (`POST /api/run/{run_id}/approve`); then SMS (and voice for urgent spoilage) goes out via a cellular provider — **no internet required on the farmer’s phone**. The **Farmer Advisor** is a separate service that reads finished plans and stored weather from Postgres/Redis and answers follow-up questions with optional LLM + Redis session history.

> **Offline last-mile:** Upstream internet loss (OpenWeather, routing APIs) is handled by fallbacks in [FallbackHandling.md](FallbackHandling.md) (Haversine distances, synthetic weather). Downstream, SMS/voice closes the loop so field actors still receive pickup times. See [§15 — Farmer & driver notifications](FallbackHandling.md#15-farmer--driver-notifications--offline-last-mile-comms).

> **Note:** OR-Tools solves a **capacitated VRP** with per-route distance limits. Truck availability and timing-style checks run in the **Validator** after solving—not as OR-Tools time-window dimensions.

For **resilience and fallback chains** (weather, routing, LLM, DB, Redis, validator retry), see [FallbackHandling.md](FallbackHandling.md) (detailed) or [ARCHITECTURE.md](ARCHITECTURE.md) (overview).

---

## Agent roles

| Agent | Role | LLM? | Primary tools |
|-------|------|------|----------------|
| **Orchestrator** | Validates inputs, resolves conflicts, packages final plan | No | LangGraph state graph |
| **Weather** | Fetches OpenWeather current + 24h forecast **per farm** (not mandis), classifies risk (normal / warning / severe). On API failure, falls back to **live_weather rules** (not scripted heat/monsoon overlays). | No | OpenWeatherMap API (optional), Redis cache |
| **Demand forecast** | 7-day demand per mandi; festival rules + optional LLM; bias correction from outcome store | Yes (optional) | Outcome store, LLM (OpenRouter / OpenAI) |
| **Inventory** | Spoilage windows from crop and temperature; optional LLM for prioritisation | Yes (optional) | Temperature-adjusted shelf life |
| **Logistics** | Capacitated VRP with distance limits; Haversine (×1.3) or Google Maps distance matrix | No | OR-Tools, distance matrix cache |
| **Validator** | Rule-based feasibility: capacity, availability, weather routes, driver hours, urgent coverage; triggers retry loop | No | Constraint checker |
| **Farmer advisor** | Plain-language answers using the current plan and stored per-farm weather; session history | Yes | LLM, plan DB, weather snapshot (Postgres + Redis), Redis session |
| **FPO notification gateway** | Holds SMS/voice until officer approves; dispatches pickup alerts (en/hi) and truck route SMS after sign-off | No | `POST /api/run/{id}/approve`, MSG91/Twilio/mock provider, `notification_logs` |

> **Weather scope:** OpenWeather is queried at each **farm** coordinate (20 in the demo fixture). **Mandis / demand points** (10 in the demo) do not get separate weather API calls; they are affected indirectly via farm risk, routing, and demand adjustments.

> **Field notifications:** Farmers need `phone`, `notify_opt_in=true`, and a route assignment. Urgent farms (&lt; 24 h spoilage) get SMS; &lt; 12 h may also get voice. Truck drivers receive SMS when `driver_phone` is set. Default provider is **mock** (logs `MOCK SMS` in backend output).

LLM agents work without API keys via rule-based fallbacks. For the best demo, provide an **OpenRouter** or **OpenAI** key.

---

## Tech stack

- **Backend:** Python 3.11, FastAPI, LangGraph, SQLAlchemy (async), OR-Tools
- **LLMs:** OpenAI-compatible API (OpenRouter / OpenAI) — optional
- **Data:** PostgreSQL, Redis (cache + sessions)
- **Frontend:** Next.js 14, React, Tailwind, Leaflet, Recharts
- **Infra:** Docker Compose

---

## Demo (6 steps)

> Stack must be running first — see [Quick Start](#quick-start) below.

> **Notifications:** Set `NOTIFY_ENABLED=true` and `NOTIFY_PROVIDER=mock` in `.env`, then `docker compose restart backend`. After a scenario run, use **Approve & Notify** on the dashboard; check `docker logs agentfarm_backend` for `MOCK SMS` lines.

### Scenario types

| Scenario | What it does |
|----------|----------------|
| **Monsoon Disruption** | Scripted heavy rain in high-risk farm zones; shelf life −20%; road legs ×1.3 |
| **Heat Wave** | Scripted temps ≥39°C; shelf life −40%; morning-delivery route bias |
| **Normal Day** | Baseline — no scenario stress overlays on shelf life or distances |
| **Live Weather** | OpenWeather at each farm (no scripted rain/temp overlay); stress derived from observed readings |
| **Validator Retry Demo** | Undersized truck fleet triggers validator retry loop (weather = Normal Day) |

### Walkthrough

1. Open **http://localhost:3000/scenario**
2. Pick a scenario — e.g. **Monsoon Disruption** for a scripted stress test, or **Live Weather** when `OPENWEATHER_API_KEY` is set → click **RUN SCENARIO →**
3. Watch **6 agent roles** execute live (Weather → Demand → Inventory → Logistics → Validator → Orchestrator) — typically ~35–90 seconds for the 20-farm demo fixture
4. Click **View Dashboard →** → check KPI cards (waste reduction vs naive baseline; typical range **20–60%** depending on scenario and seed data), map with truck routes, weather panel (**Live** vs simulated), and the **FPO Approval Gateway** panel
5. Review routes on **FARMER**, **MANDI**, and **TRANSPORT** tabs → if the plan looks good, click **Approve & Notify** (requires `NOTIFY_ENABLED=true`) → farmers and drivers receive mock SMS in backend logs
5b. **Breakdown assistance (live incident):** On the **TRANSPORT** tab, after notifications are dispatched, click **Report breakdown** on an assigned truck → review the replan preview in the **Breakdown assistance** panel → **Approve replan & notify** to send UPDATE SMS to reassigned farmers and spare driver (mock logs)
5c. **Live GPS tracking:** After **Approve & Notify**, open **Open driver GPS page** on a truck card (or `/driver/{runId}/{truckId}` on a phone) → allow location → dashboard map shows live truck markers; if the driver strays >3 km off the planned corridor for 2+ minutes, FPO and driver receive deviation SMS (mock logs)
6. Open **Advisor** → ask about the plan (e.g. mandi shortages, at-risk farms, or **weather**: “Which farms have the worst rain?”, “Where is it hottest?”)

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- An **OpenRouter** or **OpenAI** API key — recommended for LLM agents and the advisor ([openrouter.ai](https://openrouter.ai))

### 1 — Clone and configure environment

```bash
git clone <repo-url>
cd Unysis_AgentFarm

# Copy the example env file
cp .env.example .env
```

Open `.env` and fill in your keys:

```ini
# Recommended for LLM agents (Demand, Inventory, Advisor)
OPENAI_API_KEY=sk-or-v1-xxxxxxxxxxxx   # OpenRouter key OR OpenAI key

# Optional — improves accuracy, falls back gracefully without them
OPENWEATHER_API_KEY=                   # https://openweathermap.org/api
GOOGLE_MAPS_API_KEY=                   # https://console.cloud.google.com

# Pre-set for Docker Compose — do not change unless running locally
DATABASE_URL=postgresql+asyncpg://agentfarm:agentfarm@postgres:5432/agentfarm
REDIS_URL=redis://redis:6379/0
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Farmer / driver SMS + voice (offline last-mile comms)
NOTIFY_ENABLED=true              # false = no outbound messages
NOTIFY_PROVIDER=mock             # mock | msg91 | twilio
NOTIFY_REQUIRE_APPROVAL=true     # hold alerts until FPO clicks Approve & Notify
# FIELD_OFFICER_PHONE=           # optional digest SMS when human_review is true
```

> **No API key?** The demo still runs end-to-end. Weather uses scenario overlays when live weather is unavailable; Logistics falls through to Haversine if no routing key is set. Demand and Inventory use rule-based logic. The Advisor answers from structured plan data when the LLM is unavailable.

> **Live weather:** Set `OPENWEATHER_API_KEY` before `docker compose up` so the UI shows **Live (OpenWeather)** instead of simulated weather. On the scenario page, choose **Live Weather** to drive the pipeline from real-time readings at each farm (no scripted rain/temp overlay).

### 2 — Get an OpenRouteService key (2 min, free, no card)

This branch uses **OpenRouteService** as the primary road-routing source — no map data to download, no Docker memory tuning, just an API key.

1. Sign up at https://openrouteservice.org → My Account → Tokens
2. Click **Create Token** → copy the key
3. Paste into `.env`: `ORS_API_KEY=<your-key-here>`

Free tier gives **2,000 directions requests per day** with no card required. More than enough for demos and dev work.

> **What if I don't set ORS_API_KEY?** Backend silently falls through to Google (if its key is set) → Haversine x1.3. The pipeline still runs end-to-end, just with less accurate distances.

> **Self-hosting OSRM instead?** This branch still supports the self-hosted OSRM path from the `v1` branch — see "Optional: self-host OSRM" below.

### 3 — Start all services

```bash
docker compose up -d --build
```

The backend installs from a **locked** `backend/requirements.txt` (generated from `requirements.in` via `pip-compile`), so builds are reproducible.

**First build:** allow **10–20 minutes** while large wheels download (OR-Tools, LangGraph, pandas). Later rebuilds are faster when `requirements.txt` is unchanged. Ensure Docker Desktop is running and your network can reach Docker Hub and PyPI.

| Container | Port | Role |
|-----------|------|------|
| `agentfarm_frontend` | 3000 | Next.js UI |
| `agentfarm_backend` | 8000 | FastAPI + LangGraph pipeline |
| `agentfarm_postgres` | 5432 | Plans + outcome history |
| `agentfarm_redis` | 6379 | OpenWeather coordinate cache, per-run weather snapshots, distance cache, advisor sessions |
| `agentfarm_osrm` | — | **Optional** self-hosted road routing — only started with `--profile self-host` |

### Optional: self-host OSRM instead of using OpenRouteService

If you want to run road routing locally (no daily request limits, no third-party network calls) — at the cost of ~5 GB disk, ~10 GB RAM during prep, and ~15 min of one-time setup — the original OSRM workflow still works on this branch:

```powershell
# Windows
.\scripts\prepare-osrm.ps1
```
```bash
# macOS / Linux
./scripts/prepare-osrm.sh
```

Then start the stack with the `self-host` profile, which adds the `osrm` container alongside the regular four:

```bash
docker compose --profile self-host up -d
```

When both `ORS_API_KEY` and a running OSRM container are present, the backend prefers OpenRouteService (it's already a hosted answer); OSRM acts as a backup. Empty `ORS_API_KEY` + running OSRM = OSRM is used directly.

Wait ~30 seconds after containers are **Up** for the database to seed, then open **http://localhost:3000**.

### 4 — Verify everything is healthy

```bash
docker compose ps

curl http://localhost:8000/health
# Expected: {"status":"ok"}

# Interactive API docs
open http://localhost:8000/docs
```

### 5 — Stop or restart the stack

```bash
docker compose restart          # restart all services
docker compose restart backend  # reload backend code (no auto-reload in Docker)
docker compose down             # stop containers, keep data
docker compose down -v          # stop and wipe volumes (fresh start)
```

> **Port 8000:** Do not run Docker `backend` and local `uvicorn` on port 8000 at the same time — only one can bind the port. Use either Docker backend **or** `uvicorn main:app --reload` from `backend/`, not both.

---

## Python dependencies (backend)

| File | Purpose |
|------|---------|
| `backend/requirements.in` | Direct dependencies you edit |
| `backend/requirements.txt` | Locked tree for Docker and `pip install` (auto-generated) |
| `backend/requirements-dev.txt` | Adds pytest for local / CI tests |

After changing `requirements.in`, regenerate the lockfile:

```bash
cd backend
./scripts/compile-requirements.sh          # macOS / Linux
.\scripts\compile-requirements.ps1         # Windows
```

Commit both `requirements.in` and `requirements.txt` so evaluators get identical installs from `docker compose build`.

---

## Manual development setup (without Docker)

### Backend

Requires Python 3.11+ and running Postgres + Redis.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export DATABASE_URL=postgresql+asyncpg://agentfarm:agentfarm@localhost:5432/agentfarm
export REDIS_URL=redis://localhost:6379/0
export OPENAI_API_KEY=sk-or-v1-xxxxxxxxxxxx
export OPENAI_BASE_URL=https://openrouter.ai/api/v1

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

Requires Node.js 18+.

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api" > .env.local
npm run dev
```

Frontend: **http://localhost:3000**

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Recommended | — | OpenRouter or OpenAI key for LLM agents and advisor |
| `OPENAI_BASE_URL` | No | `https://api.openai.com/v1` | Use `https://openrouter.ai/api/v1` for OpenRouter |
| `OPENWEATHER_API_KEY` | No | — | Live weather; synthetic + scenario overlay without it |
| `GOOGLE_MAPS_API_KEY` | No | — | Road distances; Haversine ×1.3 fallback without it |
| `DATABASE_URL` | Yes | see `.env.example` | PostgreSQL (asyncpg) |
| `REDIS_URL` | Yes | see `.env.example` | Redis |
| `VRP_TIME_LIMIT` | No | `30` | OR-Tools solver time limit (seconds) |
| `MAX_RETRIES` | No | `2` | Validator retry cap before human review |
| `ADVISOR_TEMP` | No | `0.3` | LLM temperature for the Farmer Advisor |
| `NOTIFY_ENABLED` | No | `false` | Enable farmer/driver SMS and voice after plan completes |
| `NOTIFY_PROVIDER` | No | `mock` | `mock` (log only), `msg91`, or `twilio` |
| `NOTIFY_REQUIRE_APPROVAL` | No | `true` | Hold alerts until `POST /api/run/{id}/approve` |
| `NOTIFY_SPOILAGE_HOURS` | No | `24` | SMS farms with spoilage under this many hours |
| `NOTIFY_VOICE_SPOILAGE_HOURS` | No | `12` | Also place voice call when under this threshold |
| `NOTIFY_ALL_ROUTED` | No | `false` | If `true`, SMS all routed farms (not only urgent) |
| `FIELD_OFFICER_PHONE` | No | — | Optional pre-approval digest when `human_review` is set |
| `BREAKDOWN_ENABLED` | No | `true` | Enable live vehicle breakdown re-planning |
| `BREAKDOWN_AUTO_NOTIFY` | No | `false` | Skip second approval step after breakdown report |
| `TRACKING_ENABLED` | No | `true` | Enable live truck GPS ingest and deviation alerts |
| `TRACKING_INGEST_KEY` | No | `""` | Optional `X-Tracking-Key` header for position ingest |
| `DEVIATION_THRESHOLD_KM` | No | `3.0` | Off-route corridor width before deviation |
| `DEVIATION_DEBOUNCE_SECONDS` | No | `120` | Sustained off-route time before SMS alert |
| `DEVIATION_ALERT_COOLDOWN_MIN` | No | `15` | Minimum gap between repeat deviation alerts |
| `TRACKING_STALE_MINUTES` | No | `10` | No GPS update → stale on dashboard |

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scenario/run` | Run full scenario → plan, KPIs, agent traces, `weather_summary`, `weather_snapshot` |
| `GET` | `/api/run/{runId}` | Fetch persisted plan, summary, and approval status |
| `POST` | `/api/run/{runId}/approve` | FPO sign-off → dispatch farmer pickup + driver route SMS/voice |
| `GET` | `/api/run/{runId}/notifications` | Audit log of sent/failed notification messages |
| `GET` | `/api/run/{runId}/traces` | Per-agent traces, tools, timings, tokens |
| `GET` | `/api/run/{runId}/weather` | Stored OpenWeather snapshot for a run (Redis, then Postgres `run_logs`) |
| `POST` | `/api/advisor/query` | Ask the advisor about a finished plan (includes stored per-farm weather) |
| `POST` | `/api/outcome/log` | Log outcomes (feeds cross-run learning) |
| `POST` | `/api/run/{runId}/breakdown` | Report truck breakdown → partial re-plan preview |
| `POST` | `/api/run/{runId}/breakdown/{incidentId}/approve` | Approve replan → delta SMS to affected farmers/drivers |
| `GET` | `/api/run/{runId}/breakdown` | List breakdown incidents for a run |
| `POST` | `/api/run/{runId}/tracking/{truckId}/position` | Ingest driver GPS position |
| `GET` | `/api/run/{runId}/tracking` | Live truck positions for dashboard poll |
| `GET` | `/api/run/{runId}/tracking/deviations` | Route deviation alert history |
| `GET` | `/health` | Liveness probe |

**`weather_snapshot`** (returned by scenario run and persisted per run) includes: fetch time, weather source, aggregate summary, and **per-farm readings** (temp, rain, humidity, wind, severity). Cached in Redis (`weather_run:{run_id}`, 7-day TTL) and in Postgres `run_logs.detail_json`.

Interactive docs: **http://localhost:8000/docs**

---

## Project structure

```
Unysis_AgentFarm/
├── backend/
│   ├── agents/            # weather, demand, inventory, logistics,
│   │                      #   validator, orchestrator, advisor
│   ├── memory/            # LangGraph state (T1), outcome store (T2), sessions (T3)
│   ├── tools/             # weather_api, weather_summary, weather_store,
│   │                      #   maps_api, vrp_solver, db, notifications/
│   ├── models/            # Pydantic schemas + SQLAlchemy ORM
│   ├── routes/            # scenario, runs, advisor
│   ├── graph.py           # LangGraph StateGraph
│   └── main.py            # FastAPI entry
├── frontend/
│   └── src/
│       ├── components/    # SimulationPanel, MapView, KPIGrid, FpoApprovalPanel, …
│       ├── pages/         # scenario, dashboard, advisor, runs
│       ├── hooks/         # useScenario, useRuns, useAdvisor
│       └── utils/         # demoFixtures, formatters
├── data/                  # Seed CSVs (farms, mandis, trucks, outcomes)
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Troubleshooting

**Docker build fails (timeout, `Read timed out`, or `registry-1.docker.io` DNS errors)**  
Retry the build; network issues are often temporary. Ensure Docker Desktop is running, disable VPNs that block PyPI or Docker Hub, then:

```bash
docker compose build backend
docker compose up -d
```

**Backend container keeps restarting**

```bash
docker compose logs backend --tail 50
```

**"Pipeline error — check that the backend is running at localhost:8000"**

```bash
docker compose ps
curl http://localhost:8000/health
docker compose logs backend --tail 30
```

**LLM agents return rule-based answers only**

```bash
grep OPENAI_API_KEY .env
docker compose exec backend env | grep OPENAI
```

**Map tiles not loading**  
Uses OpenStreetMap tiles (needs internet). Markers and route polylines still render without tiles.

**Port already in use**  
Change host ports in `docker-compose.yml` (e.g. `"3001:3000"` for the frontend). Common conflicts:

- **8000** — Docker backend vs local `uvicorn` (pick one)
- **3000** — Docker frontend vs `npm run dev` (pick one)

**Backend code changes not reflected in Docker**  
Docker does not auto-reload Python like `uvicorn --reload`. After editing backend code:

```bash
docker compose build backend && docker compose up -d backend
```

Or `docker compose restart backend` if only Python files changed and the image was already rebuilt.

**Approve & Notify returns `[404] Not Found`**  
The running backend is missing the approve route (stale Docker image or port conflict with local `uvicorn`). Rebuild and restart:

```bash
docker compose build backend && docker compose up -d backend
curl http://localhost:8000/openapi.json | grep approve
```

Then run a **fresh scenario** (old runs may lack `scenario_snapshot` and fail approve with 422). See [FallbackHandling.md §15](FallbackHandling.md#15-farmer--driver-notifications--offline-last-mile-comms).

**No MOCK SMS after approve**  
Check `NOTIFY_ENABLED=true` in `.env`, restart backend, and confirm farms have `phone` + `notify_opt_in` in the scenario payload. Alerts are held until you click **Approve & Notify** when `NOTIFY_REQUIRE_APPROVAL=true` (default).

---

## Testing

```bash
# Backend pipeline smoke test (mocked weather / maps / LLM)
cd backend
pip install -r requirements-dev.txt
pytest tests/test_pipeline_smoke.py -v

# Notification + FPO approval gateway
pytest tests/test_notifications -q

# Frontend lint
cd frontend
npm run lint
```

### Pre-demo checklist

```bash
bash scripts/validate_demo.sh          # macOS / Linux
.\scripts\validate_demo.ps1            # Windows PowerShell
```

Verifies services, `/health`, seed counts, and a minimal `POST /api/scenario/run`.

### Manual testing: notifications (PowerShell)

Replace `{run_id}` with the run UUID from the dashboard URL or scenario response (e.g. `220c1e01-d45a-4d1a-ab47-14f48e41400e`).

> **Note:** `GET http://...` is not valid in PowerShell. Use `Invoke-RestMethod` or `curl.exe` below.

**1 — Check approval status**

```powershell
$runId = "220c1e01-d45a-4d1a-ab47-14f48e41400e"
Invoke-RestMethod -Uri "http://localhost:8000/api/run/$runId" | ConvertTo-Json -Depth 5
```

Look for `approval_status` (`pending` → `dispatched`) and `notifications_dispatched_at`.

**2 — Approve and dispatch (if still pending)**

From the dashboard **Approve & Notify** button, or via API:

```powershell
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/api/run/$runId/approve" `
  -ContentType "application/json" `
  -Body "{}" | ConvertTo-Json -Depth 5
```

**3 — Fetch notification audit log (who got what)**

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/run/$runId/notifications" | ConvertTo-Json -Depth 10
```

Each row includes `phone`, `channel` (`sms` / `voice`), `status`, and `message_body`. Empty `notifications: []` means nothing was sent yet (not approved, or `NOTIFY_ENABLED=false`).

**Alternative (curl on Windows):**

```powershell
curl.exe -s "http://localhost:8000/api/run/$runId/notifications"
```

**Or in a browser:** `http://localhost:8000/api/run/{run_id}/notifications`  
**Or Swagger UI:** http://localhost:8000/docs → `GET /api/run/{run_id}/notifications` → Execute.

**4 — Live mock send log (console)**

| Backend | Where to look |
|---------|----------------|
| **Docker** | `docker logs agentfarm_backend -f` — search for `MOCK SMS` / `MOCK VOICE` |
| **Local uvicorn** | Terminal running `uvicorn main:app --reload` |

Example log line:

```
INFO: ... MOCK SMS → +919900000001: Kisan Mitra: Nandi Valley - Truck tr-001 pickup ~6:30 AM...
```

Use **one** backend on port 8000 (Docker **or** local uvicorn, not both) so approve, API, and logs all hit the same process.

---

## Contributing

See the repository issues for contribution guidelines.

---

## License

MIT — see [LICENSE](./LICENSE).
