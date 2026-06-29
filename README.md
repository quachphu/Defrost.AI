# Defrosted.ai

An AI agent that finds, contacts, negotiates with, and closes rental leases on
behalf of renters. The user describes what they need once and signs the lease at
the end; the agent handles discovery, outreach, follow-up, and coordination in
between.

## Architecture

```
domain/          Pure-Python entities, value objects, events, exceptions (no frameworks)
repositories/    The only place SQL lives; one file per aggregate
agents/          LLM orchestrator + verified tools (email/sms/voice/browser)
workflows/       Temporal durable workflows (+ activities.py)
services/        Application services: orchestrate domain + repositories
api/             FastAPI routers, schemas, dependencies, middleware
infrastructure/  Async SQLAlchemy engine, Redis, S3, append-only event store
```

The core loop: describe requirements → scrape listings → contact landlords
(email → SMS → phone, with server-side verification of every send) → wait and
follow up → present confirmed options → user approves → submit offer →
coordinate lease → sign.

Two design rules are load-bearing:
- **Never trust the LLM's self-report.** Every outreach tool has a `verify()`
  that confirms the action against the provider's API before any event is
  recorded (`agents/verification.py`).
- **Append-only event store.** Every consequential action is an immutable event
  (`infrastructure/event_store.py`), giving a full audit trail.

## Running the App

**Prerequisites:** Docker and Docker Compose installed.

**Step 1 — Create a `.env` file** in the project root with your API keys:

```
GROQ_API_KEY=your_key_here
RENTCAST_API_KEY=your_key_here
```

> `RENTCAST_API_KEY` is optional — the app runs without it, listings just won't include live market data.

**Step 2 — Build and start:**

```bash
docker compose up --build
```

**Step 3 — Open the app:** http://localhost:8000

**To stop:** `Ctrl+C`, then `docker compose down`

**If the build fails or containers don't start, clean rebuild:**

```bash
docker compose build --no-cache
docker compose up -d
```

The database and JWT secret are configured automatically inside Docker — no `.env` setup required for those.

**Routes:**
- `/` — landing page (signup / login)
- `/app` — dashboard (redirects to `/` if not logged in)
- Buyers: rent vs buy analyzer + live listings + AI agent chat
- Sellers: listing dashboard + interested buyer management + AI agent chat

## Inspecting the Database with DBeaver

The postgres database runs inside Docker and is exposed on host port **5433** (not 5432, to avoid conflicts with any local postgres).

1. Open DBeaver → **New Database Connection** → choose **PostgreSQL**
2. Fill in the connection fields:

| Field    | Value       |
|----------|-------------|
| Host     | `localhost` |
| Port     | `5433`      |
| Database | `defrosted` |
| Username | `defrosted` |
| Password | `defrosted` |

3. Click **Test Connection** → then **Finish**

Tables created automatically on first run:
- `users` — registered accounts (email, hashed password, role, profile info)
- `property_listings` — seller-posted listings
- `interests` — buyer interest requests with approve/decline status

Common tasks: `make test`, `make lint`, `make typecheck`.

## Tech stack

Python 3.12 · FastAPI + Pydantic v2 · Temporal · LangGraph · Anthropic Claude ·
Playwright/Browserbase · SendGrid · Twilio · Bland.ai · PostgreSQL 16 +
PostGIS + pgvector · Redis · Elasticsearch · S3 · structlog.

## Notes on the implementation

A few places diverge from the prose spec where the prose was internally
inconsistent; each is documented at the site:

- `repositories/listing_repository.py`: `_is_same_unit` also checks rent within
  5% (the unit test requires it), and reads/writes geography via the single
  `location` column the migration defines.
- `agents/tools/email_tool.py`: imports `Settings` from the correct depth and
  types its injected `RateLimiter`.
- `activities.py` exists because the workflow imports it; steps that depend on
  capabilities not yet built (per-site scrapers, DocuSign) raise a precise
  `NotImplementedError` rather than returning empty results.

The fully runnable unit suite (`tests/unit`) covers the dedup algorithm and the
email verification step. The remaining provider integrations require live
services and the `infra` extra.
