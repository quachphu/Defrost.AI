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

## Setup

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,infra]"     # full stack
cp .env.example .env              # fill in secrets
make up                           # postgres, redis, temporal, elasticsearch
make migrate                      # apply the schema
make dev                          # run the API
```

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
