# Defrosted.ai — Architecture & Phase-1 Build Summary

> Status snapshot for planning the next phase. Describes what exists, at what
> fidelity, and where the open work is.

## 1. Product in one line
An AI agent that takes a renter's requirements once, then autonomously discovers
listings, contacts landlords (email → SMS → phone), follows up, surfaces
confirmed options for human approval, and coordinates the lease to signing.

## 2. Tech stack (implemented / declared)
Python 3.12 · FastAPI + Pydantic v2 · Temporal (durable workflows) ·
LangGraph + Anthropic Claude (agent loop) · Playwright/Browserbase (scraping) ·
SendGrid (email) · Twilio (SMS) · Bland.ai (voice) · PostgreSQL 16 + PostGIS +
pgvector · Redis · Elasticsearch · S3 · JWT (python-jose) · structlog.

Declared in `pyproject.toml`: core deps + `infra` extra (heavy runtime) +
`dev` extra (test/lint).

## 3. Layered architecture

```
┌───────────────────────────────────────────────────────────────────┐
│ API LAYER  (api/)                                                   │
│  routers: searches, listings, approvals, leases                     │
│  middleware: RequestID → SecurityHeaders → RateLimit → CORS         │
│  dependencies.py = composition root (JWT auth, DI wiring)           │
│  schemas/ = wire format (NOT domain models)                         │
└───────────────┬─────────────────────────────────────────────────────┘
                │ calls
┌───────────────▼─────────────────────────────────────────────────────┐
│ SERVICE LAYER  (services/)                                          │
│  RentalSearchService · OutreachService · LeaseService                │
│  business rules, state-machine transitions, txn boundaries           │
└───────┬───────────────────────────┬─────────────────────────────────┘
        │                           │
        │ orchestrates              │ uses
┌───────▼─────────────┐   ┌─────────▼────────────────────────────────┐
│ WORKFLOW LAYER       │   │ AGENT LAYER  (agents/)                   │
│ (workflows/ +        │   │  orchestrator (LangGraph tool loop)      │
│  activities.py)      │   │  tools/: email, sms, voice, browser      │
│  Temporal durable    │   │          (each has execute + VERIFY)     │
│  RentalSearchWorkflow│   │  verification.py (record only if         │
│  + Outreach/Lease    │   │   provider confirms)                     │
│  child workflows     │   │  prompts.py                              │
└───────┬──────────────┘   └─────────┬────────────────────────────────┘
        │                            │
        │ persists via               │ writes events via
┌───────▼────────────────────────────▼────────────────────────────────┐
│ REPOSITORY LAYER  (repositories/)  — the ONLY place SQL lives        │
│  listing · rental_search · landlord · lease · agent_run(outreach)    │
└───────┬───────────────────────────────────────────────────────────────┘
        │
┌───────▼───────────────────────────────────────────────────────────────┐
│ DOMAIN LAYER  (domain/)  — pure Python, no frameworks                 │
│  models · value_objects (Money/Address/PhoneNumber) · events ·        │
│  exceptions                                                           │
└───────┬───────────────────────────────────────────────────────────────┘
        │
┌───────▼───────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE  (infrastructure/)                                     │
│  database (async SQLAlchemy) · cache (Redis + RateLimiter) ·          │
│  storage (S3) · event_store (append-only)                             │
└───────────────────────────────────────────────────────────────────────┘
```

## 4. Core runtime flow

```
POST /searches
  → RentalSearchService.create_search
      → enforce max 3 active searches/user
      → LLM parses free text → RentalRequirements
      → persist RentalSearch (PENDING) + SearchStartedEvent
      → start Temporal RentalSearchWorkflow

RentalSearchWorkflow (durable, top-to-bottom recipe):
  1. scrape_listings        (Browserbase + Playwright)
  2. deduplicate_listings   (PostGIS proximity + address sim + rent tolerance)
  3. contact_landlords      (email; each send VERIFIED before event recorded)
  4. wait_for_responses     (48–96h, follow-ups, channel escalation)
  5. build_approval_options → wait_condition for user signal (48h timeout)

POST /searches/{id}/approve  → Temporal signal user_approved_listing
  6. submit_offer
  7. coordinate_lease       (DocuSign) → LeaseSignedEvent
```

## 5. Two load-bearing invariants
- **Never trust the LLM's self-report.** Every tool implements `execute()` +
  `verify()`. An outreach event is appended only after `verify()` confirms
  against the provider's API (`agents/verification.py`). Explicit defense
  against fabricated tool success.
- **Append-only event store.** Every consequential action emits an immutable,
  per-search monotonically-sequenced event (`infrastructure/event_store.py`,
  `domain_events` with `UNIQUE(rental_search_id, sequence)`). Audit trail /
  legal record / debugging source of truth.

## 6. Data model (Postgres, migration `001_initial_schema`)
`users`, `rental_searches` (requirements JSONB), `landlords` (behavioral metrics
+ `vector(1536)` behavior embedding), `listings` (flat address cols +
`GEOGRAPHY(POINT,4326)` location, GIST index, `UNIQUE(source, source_listing_id)`),
`outreach_attempts`, `domain_events` (append-only), `leases` (address JSONB
snapshot). Extensions: `uuid-ossp`, `postgis`, `vector`.

State machine (`RentalSearch.can_transition_to`):
`PENDING → SEARCHING → OUTREACHING → AWAITING_APPROVAL → APPROVED → SIGNING → COMPLETED`;
any state `→ FAILED`.

## 7. File inventory with implementation fidelity

| Component | Status |
|---|---|
| `domain/value_objects.py`, `models.py`, `events.py` | Complete (verbatim from spec) |
| `domain/exceptions.py` | Complete (added) |
| `repositories/base.py`, `listing_repository.py` | Complete (verbatim + documented fixes) |
| `repositories/rental_search`, `landlord`, `lease`, `agent_run` | Complete, functional, schema-aligned |
| `agents/tools/base.py`, `email_tool.py` | Complete (verbatim + import/typing fix) |
| `agents/tools/sms_tool.py`, `voice_tool.py` | Complete, real provider calls (Twilio/Bland) |
| `agents/tools/browser_tool.py` | Skeleton — interface complete; per-site parsers raise `NotImplementedError` |
| `agents/orchestrator.py` | Functional skeleton — LangGraph verified tool-loop |
| `agents/verification.py`, `prompts.py` | Complete |
| `workflows/rental_search_workflow.py` | Complete (verbatim) |
| `workflows/outreach_workflow.py`, `lease_workflow.py` | Complete (child workflows) |
| `activities.py` | Skeletons — self-contained steps delegate to services; provider-dependent steps raise precise `NotImplementedError` |
| `services/rental_search_service.py` | Complete (create/get/approve, DI'd parser + workflow gateway) |
| `services/outreach_service.py`, `lease_service.py` | Functional, the composable units |
| `api/` (routers, schemas, dependencies, middleware, app) | Complete & importable |
| `infrastructure/` (database, cache+RateLimiter, storage, event_store) | Complete |
| `alembic/` migration + env | Complete |
| `tests/unit` (dedup + email verify) | Complete & passing (8/8) |
| `docker-compose`, `Makefile`, `pyproject`, `.env.example`, `.gitignore`, `README` | Complete |

## 8. Verification status
- `ruff check src tests` → clean
- `pytest tests/unit` → 8 passed
- Full-tree byte-compile → clean
- All modules with installed deps import cleanly
- **Not yet run:** live DB/Temporal integration, `mypy --strict`,
  `infra`-extra-only modules at runtime.

## 9. Intentional deviations from the prose spec (each documented in-code)
1. `listing_repository._is_same_unit` adds a rent-within-5% check (required by
   the spec's own unit test; prose checked address only).
2. Listing repo reads/writes geography via the single `location` column with
   `ST_MakePoint`/`ST_X`/`ST_Y` + a `_row_to_listing` mapper (prose
   `SELECT *`/`Listing(**row)` was incompatible with the DDL).
3. `email_tool` imports `Settings` from correct depth and types the injected
   `RateLimiter`.
4. JSONB writes use `json.dumps` + `CAST(... AS JSONB)` (asyncpg can't
   auto-encode dicts).
5. `activities.py` created (workflow imports it); unbuilt capabilities fail
   loudly instead of returning empty data.

## 10. Next-phase work (the real gaps)

### Critical path to a working vertical slice
1. **Browser scraping adapters** — per-site (Zillow/Craigslist/Facebook/Hotpads)
   Playwright+Browserbase parsers feeding `Listing` ingestion + geocoding to
   populate `location`. Unblocks the entire workflow.
2. **Inbound email parsing (Nylas)** — `wait_for_responses_activity` needs reply
   ingestion + sentiment classification to mark listings RESPONDED/confirmed.
3. **Wire activities → services** — replace `NotImplementedError` skeletons with
   real session-scoped service calls once scrape data exists.
4. **Landlord enrichment** — resolve landlord email/phone/handle from listings so
   outreach has a target; populate `landlords` profile/metrics loop.
5. **HumanApproval persistence** — domain model exists but no table/repository;
   needed for the approval audit and the `approvals` router read side.
6. **Offer + DocuSign** — `submit_offer_activity`, `coordinate_lease_activity` +
   `LeaseService.record_signed_lease` integration.

### Supporting / hardening
7. Temporal worker process (registers workflows + activities; not yet written).
8. `users` table exists but no user repo / Clerk webhook handler.
9. Elasticsearch + pgvector provisioned but unused (listing full-text/geo search;
   landlord behavior embeddings).
10. Integration tests (`tests/integration/api`, `/workflows` dirs exist, empty),
    `mypy --strict` pass, observability (LangSmith/Sentry) wiring.
11. Channel-escalation policy + ghost detection (modeled in `outreach_workflow`
    loop, not yet backed by real send/verify).

### Architectural decisions to make in planning
- Where landlord contact-info resolution lives (scrape-time vs separate
  enrichment activity).
- Idempotency/concurrency for event-store sequence assignment under parallel
  activities (currently `MAX+1`; needs retry-on-conflict or advisory lock at
  scale).
- Multi-listing parallelism: fan-out `OutreachWorkflow` child workflows vs single
  activity loop.
- Auth: spec mentions both JWT and Clerk webhooks — reconcile.
