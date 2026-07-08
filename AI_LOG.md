# AI Collaboration Log

## 1. Overview

AI was used as an implementation accelerator during this project, not as an
autonomous builder. The scope, architecture, technology choices, and monitoring
semantics were defined first; AI then generated scaffolding and first-draft code
for each layer (FastAPI backend, APScheduler job, React/Tailwind dashboard,
Docker configuration). Every generated unit was read, run, and corrected before
it was accepted. The primary tool was Claude (via the Claude Code CLI), which
could edit files and run commands directly, with a human reviewing each diff.
The most valuable use of AI was producing a large amount of boilerplate quickly
across an unfamiliar layer (frontend/CSS tooling); the most necessary human work
was validating behaviour at the seams — container-to-browser networking,
sync/async boundaries, dependency versions, and failure semantics — where the
generated code was plausible but wrong.

## 2. Engineering Ownership

The following remained the developer's responsibility throughout. AI accelerated
the typing, not these decisions:

- **Architecture.** Three-service split (frontend / backend / Postgres) and the
  single-origin reverse-proxy design so the browser talks to one host. Verified
  in `docker-compose.yml`, `frontend/nginx.conf`, and `frontend/src/api.ts`.
- **Technology selection.** FastAPI + SQLAlchemy + APScheduler + httpx + Postgres
  on the backend; React + Vite + TypeScript + Tailwind on the frontend; nginx to
  serve the build. Versions were pinned deliberately (`backend/requirements.txt`,
  `frontend/package.json`).
- **API behaviour.** The endpoint surface and contracts (`POST/GET/DELETE /urls`,
  `GET /status`, `GET /history/{id}`, `POST /check-now`, `GET /health`) as
  implemented in `backend/app/main.py`.
- **Monitoring semantics.** The definition of "up" (`status_code < 400`), the
  decision to record latency even on failure, and catching `httpx.RequestError`
  specifically. Implemented in `backend/app/checker.py`.
- **Backend/frontend integration.** Wiring the dashboard to the backend through
  the `/api` prefix, proxied by nginx in Docker and by Vite in dev.
- **Validation and debugging.** Every generated file was reviewed; the ping logic
  was executed against a live healthy URL and an unresolvable one to confirm the
  up/down paths (see §6.4 and README testing steps).
- **Deployment approach.** The cloud topology sketch (`deploy/main.tf`, README)
  is a developer-authored design decision; AI was not relied on for it.

## 3. AI Tools Used

| Tool | Purpose |
| --- | --- |
| Claude (Claude Code CLI) | Generate scaffolding and first-draft code; edit files and run commands under review |
| Claude (chat) | Discuss design trade-offs (sync vs async scheduler, single-origin vs CORS) before implementation |

## 4. AI-Assisted Development Workflow

| Stage | Developer Responsibility | AI Assistance |
| --- | --- | --- |
| Architecture | Defined project scope; chose the three-service, single-origin design; reviewed the proposal | Proposed initial folder structure and layer breakdown |
| Backend | Defined API contracts and business logic; validated endpoints | Generated the FastAPI scaffold and route handlers |
| Scheduler | Defined monitoring behaviour (interval, up/down rule, failure handling) | Drafted the APScheduler job and httpx ping loop |
| Frontend | Integrated components, verified live polling and UI states | Generated React components and Tailwind styling |
| Docker | Validated container networking and startup ordering | Generated Dockerfiles, `docker-compose.yml`, and nginx config |
| Documentation | Reviewed and finalized README / this log | Produced initial drafts |

## 5. Representative Prompts

These illustrate the collaboration pattern (define intent → generate → correct).

1. **Architecture framing:**
   > "Uptime monitor MVP: register URLs, ping each on a schedule, store status
   > code + response time + timestamp per check, show live up/down on a dashboard,
   > run with one `docker compose up`. Stack: FastAPI + SQLAlchemy + APScheduler +
   > httpx + Postgres, and React + Vite + TypeScript + Tailwind. Propose the folder
   > structure before writing code."

2. **Backend with explicit semantics:**
   > "Generate the FastAPI backend and a background job that pings every URL every
   > 60 seconds and writes one `health_checks` row per URL per tick. A URL is 'up'
   > if it responds with status < 400; connection failures are 'down' with a null
   > status code."

3. **Networking constraint (a correction folded into the prompt):**
   > "The browser can't resolve the Docker service name. Make the frontend call a
   > relative `/api` path and have nginx reverse-proxy `/api/*` to the backend, so
   > the browser only talks to one origin."

4. **Failure-semantics refinement:**
   > "Don't mark any HTTP response as up — use status < 400. Measure response time
   > with perf_counter so failures still get a duration, and catch
   > `httpx.RequestError` instead of a bare except."

## 6. Course Corrections

### 6.1 Async scheduler mixed with a sync database session

**Problem.** The first draft used `AsyncIOScheduler` and `httpx.AsyncClient` but
kept a synchronous SQLAlchemy session inside the async job, and started the
scheduler from the deprecated `@app.on_event("startup")` hook.

**Why the AI suggestion was insufficient.** A blocking `db.query(...)` inside an
async task blocks the event loop, so the async machinery added complexity with no
benefit; `on_event` is deprecated in current FastAPI.

**Developer decision.** For this scale (dozens of URLs, once a minute), use a
thread-based `BackgroundScheduler` with a sync `httpx.Client` and a normal
session, and move startup/shutdown into a lifespan context manager.

**Final outcome.** Implemented in `scheduler.py` (`BackgroundScheduler`),
`checker.py` (sync `httpx.Client`), and `main.py` (`asynccontextmanager`
lifespan). No event-loop blocking.

### 6.2 Frontend calling the Docker service name from the browser

**Problem.** The generated fetch layer used `http://backend:8000` as the API base.
`backend` resolves only inside the Compose network, but `fetch` runs in the
browser, so every request failed with `ERR_NAME_NOT_RESOLVED`.

**Why the AI suggestion was insufficient.** Its fallback — hardcode
`http://localhost:8000` and add CORS — creates a permanent two-origin setup that
breaks whenever the backend host changes.

**Developer decision.** Adopt a single-origin reverse proxy: the frontend calls a
relative `/api` path; nginx proxies `/api/*` to `http://backend:8000` server-side
(where the name resolves), and Vite mirrors this in dev.

**Final outcome.** `frontend/src/api.ts` uses `/api`; `frontend/nginx.conf` and
`vite.config.ts` handle the proxying. CORS is a non-issue.

### 6.3 Tailwind PostCSS plugin/version mismatch

**Problem.** The generated `postcss.config.js` referenced `@tailwindcss/postcss`
(Tailwind v4) while `package.json` pinned Tailwind v3, so `npm run build` failed
with "trying to use `tailwindcss` directly as a PostCSS plugin."

**Why the AI suggestion was insufficient.** It blended v3 and v4 setup steps,
producing a config that matched neither installed version.

**Developer decision.** Standardize on Tailwind v3 and make the config consistent
with it.

**Final outcome.** `postcss.config.js` uses the `tailwindcss` plugin,
`package.json` pins `tailwindcss@^3.4.17`, and the build passes.

### 6.4 Uptime detection semantics

**Problem.** The first pinger treated any HTTP response as "up," recorded latency
only on success, and used a bare `except Exception`.

**Why the AI suggestion was insufficient.** For a monitor, a 5xx is not "up"; a
bare except hides real errors; and discarding timing on failure loses the
time-to-failure signal.

**Developer decision.** Define up as `status_code < 400`, measure latency with
`time.perf_counter()` around the request so failures are timed, and catch
`httpx.RequestError` specifically.

**Final outcome.** Implemented in `checker.py:check_one`. Verified by running the
function against `https://example.com` (returned 200 / up) and an unresolvable
domain (returned null status / down).

## 7. Engineering Decisions

| Decision | Reasoning |
| --- | --- |
| Sync `BackgroundScheduler`, not async | Simpler and correct at this scale; async added event-loop hazards with no benefit |
| Single-origin nginx `/api` proxy over CORS | Removes browser-to-backend host coupling; same pattern maps to the cloud sketch |
| Tailwind v3, pinned | Stable, well-documented config; avoids v3/v4 mixing |
| `is_up = status_code < 400`; latency recorded on failure | A meaningful up/down rule for a monitor, plus a time-to-failure signal |
| `create_all` on startup, no migrations | Two tables in an MVP; Alembic would be over-engineering |
| First check fires immediately on startup | Dashboard is populated without waiting a full interval |
| `wait_for_db` retry + Postgres healthcheck | `depends_on` alone waits for container start, not DB readiness |


