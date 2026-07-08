# Uptime Monitor

A lightweight full-stack uptime monitor. It periodically pings a list of registered
URLs, records each check (HTTP status code, response time, timestamp), and shows the
current up/down state of every URL on a live dashboard.

Built as a strict MVP — clean, working, end-to-end — and orchestrated to spin up with a
single `docker compose up`.

> **AI collaboration note:** This project was built by leaning heavily on an AI assistant
> (Claude / Claude Code). See **[AI_LOG.md](./AI_LOG.md)** for the raw prompts, the mistakes
> the AI made, and how they were corrected — that log is the "peek behind the curtain".

---

## Tech Stack

| Layer            | Choice                                             |
| ---------------- | -------------------------------------------------- |
| Backend API      | Python · FastAPI · SQLAlchemy · Pydantic v2        |
| Scheduler        | APScheduler (`BackgroundScheduler`) + httpx        |
| Database         | PostgreSQL 16                                       |
| Frontend         | React 18 · Vite · TypeScript · Tailwind CSS        |
| Frontend serving | nginx (static build + `/api` reverse proxy)        |
| Orchestration    | Docker & Docker Compose                            |

---

## Architecture

```
                Browser (localhost:3000)
                        │
                        ▼
        ┌───────────────────────────────┐
        │  frontend (nginx)             │
        │   • serves the React build    │
        │   • proxies /api/* ──────────┐│
        └──────────────────────────────┼┘
                                        ▼
        ┌───────────────────────────────┐
        │  backend (FastAPI :8000)      │
        │   • REST API                  │
        │   • BackgroundScheduler ──────┼──► pings each URL every 60s
        └───────────────┬───────────────┘
                        ▼
        ┌───────────────────────────────┐
        │  postgres (:5432)             │
        │   urls · health_checks        │
        └───────────────────────────────┘
```

The browser only ever talks to a single origin (`localhost:3000`). nginx proxies
`/api/*` to the backend container over the Compose network, so the frontend never needs
to know the backend's real host.

---

## Folder Structure

```
uptime-monitor/
├── backend/                 # FastAPI app + pinger + scheduler
│   ├── app/
│   │   ├── main.py          # FastAPI app, routes, lifespan
│   │   ├── database.py      # engine, session, wait_for_db
│   │   ├── models.py        # URL + HealthCheck tables
│   │   ├── schemas.py       # Pydantic request/response models
│   │   ├── crud.py          # DB queries (incl. latest-status join)
│   │   ├── checker.py       # httpx ping logic
│   │   └── scheduler.py     # APScheduler 60s job
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # React + Vite + Tailwind dashboard
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api.ts
│   │   └── components/
│   ├── Dockerfile           # multi-stage build -> nginx
│   └── nginx.conf
├── deploy/main.tf           # hypothetical AWS deployment sketch
├── docker-compose.yml
├── README.md
└── AI_LOG.md                # AI collaboration log (required deliverable)
```

---

## 1-Line Setup

From the repository root:

```bash
docker compose up --build
```

Then open:

| Service        | URL                              |
| -------------- | -------------------------------- |
| **Dashboard**  | http://localhost:3000            |
| Backend API    | http://localhost:8000            |
| API docs       | http://localhost:8000/docs       |

The backend waits for Postgres to be healthy, creates its tables on startup, and fires
the first round of health checks immediately (so the dashboard isn't blank for the first
minute). Checks then repeat every 60 seconds; the dashboard auto-refreshes every 10.

---

## Testing Steps — verify UP and DOWN tracking

The goal is to prove the monitor correctly detects and renders **both** an up state and a
down state. You can do this entirely from the dashboard.

1. **Start the stack:** `docker compose up --build`, then open http://localhost:3000.

2. **Add a healthy URL.** In the input box type `https://example.com` and click **Add URL**.

3. **Add a broken URL.** Add `https://this-domain-definitely-does-not-exist-12345.com`
   (DNS will not resolve → the check fails).

4. **Watch the dashboard.** Within a few seconds (the first check runs immediately) you
   should see:
   - `https://example.com` → **Up** badge, status `200`, a response time in ms.
   - the broken URL → **Down** badge, status `—` (no HTTP response), still timestamped.

   The dashboard re-polls every 10 seconds, and the backend re-checks every 60, so the
   values stay live.

5. **Force an immediate re-check (optional).** Instead of waiting for the 60s tick:

   ```bash
   curl -X POST http://localhost:8000/check-now
   ```

6. **Verify persistence / history (optional).** Every individual check is stored. Inspect
   the raw history for a URL (id `1` here):

   ```bash
   curl http://localhost:8000/history/1 | jq
   ```

   You'll see one row per check with `status_code`, `response_time_ms`, `is_up`, and
   `checked_at`.

### Quick API-only smoke test (no browser)

```bash
# register a good and a bad URL
curl -X POST http://localhost:8000/urls -H 'Content-Type: application/json' -d '{"url":"https://example.com"}'
curl -X POST http://localhost:8000/urls -H 'Content-Type: application/json' -d '{"url":"https://this-domain-definitely-does-not-exist-12345.com"}'

# trigger a check and read the latest status
curl -X POST http://localhost:8000/check-now
curl http://localhost:8000/status | jq
```

---

## API Endpoints

| Method   | Path            | Purpose                                        |
| -------- | --------------- | ---------------------------------------------- |
| `POST`   | `/urls`         | Register a URL (`{"url": "..."}`)              |
| `GET`    | `/urls`         | List registered URLs                           |
| `DELETE` | `/urls/{id}`    | Remove a URL and its checks                    |
| `GET`    | `/status`       | Latest health state per URL (dashboard feed)   |
| `GET`    | `/history/{id}` | Recent check history for one URL               |
| `POST`   | `/check-now`    | Trigger an immediate round of checks           |
| `GET`    | `/health`       | Liveness probe                                 |

**"Up" definition:** a URL is UP when it returns an HTTP response with status `< 400`.
Connection failures (DNS, refused, timeout, TLS) have no status code and are recorded as
DOWN.

---

## Deployment Sketch

For a real (still minimal) cloud deployment on AWS I'd keep the same three tiers:

- **Database — RDS for PostgreSQL** (`db.t4g.micro`). The one piece worth not self-hosting;
  managed backups and failover for near-zero effort.
- **Backend — ECS Fargate**, one always-on task running the backend image from ECR. The
  APScheduler loop lives inside the same container, so a single task both serves the API
  and runs the 60s checks — no separate worker needed at this scale. An ALB fronts it.
- **Frontend — S3 + CloudFront.** The `npm run build` static bundle goes to S3; CloudFront
  serves it and routes `/api/*` to the backend ALB — the exact same single-origin pattern
  the local nginx uses, so no code changes between local and cloud.

A trimmed, illustrative Terraform version of this topology lives in
[`deploy/main.tf`](./deploy/main.tf). It is a sketch (no multi-AZ, secrets manager, WAF, or
autoscaling) meant to show cloud topology, not production hardening.

Scaling up later is mostly turning knobs: bump the ECS desired count (and move the
scheduler to its own task / EventBridge schedule so checks aren't duplicated across
replicas), enable RDS multi-AZ, and add an autoscaling policy.
