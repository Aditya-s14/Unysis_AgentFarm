# Contributing to AgentFarm Optimizer

Thanks for contributing. This project is a 3-day hackathon build with five team members — keep changes focused, small, and reviewable.

---

## Branch Strategy

All work branches from `develop`. `main` is release-only.

- `feature/<short-description>` — new features (e.g. `feature/advisor-hindi-output`)
- `bugfix/<short-description>` — bug fixes (e.g. `bugfix/vrp-timeout-on-retry`)
- `chore/<short-description>` — infra, refactors, docs, tooling (e.g. `chore/add-lint-workflow`)

Merge flow: `feature/*` -> `develop` (squash) -> `main` (merge commit on release).

---

## Commit Messages — Conventional Commits

```
<type>(<optional scope>): <imperative summary>

<optional body — what and why, not how>
```

Types:

| Type | Use for |
|---|---|
| `feat` | New user-facing feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `chore` | Tooling, config, dependencies |
| `refactor` | Code restructure, no behavior change |
| `test` | Adding or fixing tests |
| `perf` | Performance improvement |

Examples:

```
feat(advisor): add Hindi output path with session locale
fix(vrp): enforce 30s time limit on retry solves
docs(architecture): document outcome feedback loop
chore(ci): add black + flake8 to lint workflow
```

**Do not add AI co-author trailers** (no `Co-Authored-By: Claude ...`). Commits should carry only human authors.

---

## Local Setup Checklist

- [ ] `git clone` and `cd Unysis_AgentFarm`
- [ ] `cp .env.example .env` and fill in `OPENWEATHER_API_KEY`, `OPENAI_API_KEY`
- [ ] `docker compose up -d` -> verify `curl localhost:8000/health` returns 200
- [ ] `cd backend && pip install -r requirements.txt && pytest` passes
- [ ] `cd frontend && npm install && npm run dev` renders at `localhost:3000`
- [ ] Pre-commit hooks installed (if configured): `pre-commit install`

---

## Code Style

### Python (backend)

- **black** — line length 100, run on save
- **isort** — profile `black`
- **flake8** — baseline PEP 8, max line length 100
- **mypy** — strict on `backend/src` (or `backend/`); type hints everywhere
- **Pydantic** for every data model; no raw dicts crossing module boundaries

Run locally:

```bash
cd backend
black . && isort . && flake8 . && mypy .
```

### TypeScript / JavaScript (frontend)

- **eslint** — Next.js default config + strict TS rules
- **prettier** — run on save
- Strict TS mode on; functional components with hooks only

Run locally:

```bash
cd frontend
npm run lint && npm run format
```

---

## Testing Expectations

- **Every new agent or tool** ships with at least one unit test (mock external APIs).
- **Bug fixes** include a regression test that fails before the fix.
- **Integration test** — at least one full-pipeline test per scenario template must stay green.
- **Frontend** — components with logic (not pure layout) get a test.

CI runs `pytest --cov` on backend and `npm test` + `npm run build` on frontend for every push and PR.

---

## Pull Request Template

Every PR opens with this template (see `.github/PULL_REQUEST_TEMPLATE.md`):

- **Summary** — one or two sentences: what and why
- **Changes** — bullet list of concrete changes
- **Testing** — what you ran, what passed, how to reproduce
- **Screenshots** — required for any UI change (before/after if applicable)
- **Checklist** — tests pass, linted, docs updated, no secrets committed

---

## Review Workflow

1. Open PR against `develop` (never directly against `main`).
2. CI must be green — test, lint, build jobs all passing.
3. **One approval required** from another team member.
4. **Squash merge** to `develop` with the PR title as the commit message (Conventional Commits format).
5. Delete the branch after merge.
6. Release PRs (`develop` -> `main`) are merge commits and require two approvals.

---

## Reporting Issues

Use GitHub Issues with a clear title, reproduction steps, expected vs actual behavior, and environment info (OS, Python/Node version, Docker version). Label appropriately (`bug`, `enhancement`, `question`, `infra`).
