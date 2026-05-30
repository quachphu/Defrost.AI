# DEFROSTED.AI — PRODUCTION CODEBASE PROMPT
### For: Anthropic Claude Opus 4.8 Coding Agent
### Author: Engineering spec derived from system design session

---

## 0. KARPATHY RULES — APPLY EVERYWHERE, NO EXCEPTIONS

These rules override any other instinct toward cleverness. Read them before writing a single line.

```
1. SIMPLE > CLEVER.
   If you can write it in 10 lines without abstraction, do not write a class.
   If a function needs a docstring longer than the function itself, the function is wrong.

2. EXPLICIT > IMPLICIT.
   No magic. No metaclasses. No __init_subclass__ tricks. No decorators that hide
   control flow. If something happens, you should be able to read exactly where and why
   it happens in a straight line from top to bottom.

3. FLAT > NESTED.
   Maximum 2 levels of class inheritance. Prefer composition over inheritance everywhere.
   If your class hierarchy has 4 levels, you made a mistake 3 levels ago.

4. NAME THINGS PRECISELY.
   contact_landlord_via_email() not send(). landlord_email_response_timeout_seconds not t.
   A reader should understand what a variable holds without reading its assignment.

5. NO PREMATURE ABSTRACTION.
   Don't create a base class or interface until you have 3 concrete implementations that
   actually need it. Write the 3 concrete things first, then extract the common shape.

6. EVERY FUNCTION DOES ONE THING.
   If you write "and" in a function name, split it. get_and_validate_listing() → two
   functions. The test for this: can you test this function in complete isolation?

7. FAIL LOUDLY AND EARLY.
   raise ValueError("landlord_id cannot be None — got None from outreach pipeline")
   is better than silently returning None and failing 3 layers later.
   Every function that can fail must say exactly WHY it failed.

8. COMMENTS EXPLAIN WHY, NOT WHAT.
   # Verify server-side because we never trust the LLM's self-report of tool success
   NOT: # call verify function

9. TESTS TEST BEHAVIOR, NOT IMPLEMENTATION.
   Test what the function guarantees to callers. Not which internal methods it calls.
   If refactoring internals breaks your tests, your tests are wrong.

10. KNOW WHAT EVERY LINE DOES.
    If you write a line of code you cannot explain completely, delete it.
    No cargo-cult patterns. No "I saw this in a tutorial."
```

---

## 1. PROJECT OVERVIEW

**Product:** Defrosted.ai — an AI agent that finds, contacts, negotiates with, and closes
rental leases on behalf of renters. The user inputs requirements once and signs the lease
at the end. The agent handles everything in between.

**Core loop:**
```
User describes requirements
  → Agent searches listings (browser automation)
  → Agent contacts landlords (email + phone + SMS)
  → Agent tracks responses and follows up
  → Agent presents confirmed options to user
  → User approves preferred option
  → Agent coordinates lease documentation
  → User signs
  → Done
```

**Scale target:** Design for 1M concurrent users from day 1 in architecture.
Build for 1,000 users in implementation (don't pre-optimize, but don't make choices
that require a rewrite at 100K).

---

## 2. TECH STACK (NON-NEGOTIABLE)

```
Language:        Python 3.12
API framework:   FastAPI + Pydantic v2
Workflow engine: Temporal.io (durable agent workflows)
Agent graph:     LangGraph (stateful multi-step agent)
LLM:             Anthropic Claude (claude-sonnet-4-20250514 default, claude-opus-4-8 for complex reasoning)
Browser:         Playwright + Browserbase (managed sessions)
Voice:           Bland.ai SDK
Email:           SendGrid (outbound) + Nylas (inbound parsing)
SMS:             Twilio
Database:        PostgreSQL 16 + PostGIS (via asyncpg + SQLAlchemy 2.0 async)
Cache:           Redis 7 (via redis-py async)
Vector store:    pgvector extension on Postgres
Search:          Elasticsearch 8 (listing full-text + geo)
Queue:           AWS SQS (early stage), Kafka (post Series A)
Storage:         AWS S3 (boto3)
Auth:            JWT (python-jose) + Clerk webhooks
Observability:   LangSmith (LLM traces) + Sentry (errors) + structlog (structured logs)
Testing:         pytest + pytest-asyncio + respx (HTTP mocking) + factory_boy
```

---

## 3. PROJECT FILE STRUCTURE

Build this exact structure. No deviations without documented reason.

```
defrosted/
├── pyproject.toml
├── .env.example
├── alembic/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── domain/
│   │   ├── repositories/
│   │   └── agents/
│   └── integration/
│       ├── api/
│       └── workflows/
└── src/
    └── defrosted/
        ├── __init__.py
        ├── config.py                  # All settings, no hardcoded values anywhere
        ├── domain/                    # Pure Python — NO framework imports
        │   ├── __init__.py
        │   ├── models.py              # Core domain entities (Pydantic)
        │   ├── events.py              # Immutable domain events (event sourcing)
        │   ├── value_objects.py       # Money, Address, PhoneNumber, etc.
        │   └── exceptions.py         # Domain-specific exceptions
        ├── repositories/              # Database access — one file per aggregate
        │   ├── __init__.py
        │   ├── base.py               # BaseRepository with common patterns
        │   ├── listing_repository.py
        │   ├── landlord_repository.py
        │   ├── rental_search_repository.py
        │   ├── lease_repository.py
        │   └── agent_run_repository.py
        ├── agents/                    # AI agent layer
        │   ├── __init__.py
        │   ├── orchestrator.py       # LangGraph state machine
        │   ├── tools/
        │   │   ├── __init__.py
        │   │   ├── base.py           # AgentTool interface
        │   │   ├── browser_tool.py   # Listing scraper
        │   │   ├── email_tool.py     # Landlord outreach
        │   │   ├── voice_tool.py     # Phone calls
        │   │   └── sms_tool.py       # SMS follow-up
        │   ├── verification.py       # Server-side action verification
        │   └── prompts.py            # All LLM prompts in one place
        ├── workflows/                 # Temporal workflow definitions
        │   ├── __init__.py
        │   ├── rental_search_workflow.py
        │   ├── outreach_workflow.py
        │   └── lease_workflow.py
        ├── services/                  # Application services (orchestrate domain + repos)
        │   ├── __init__.py
        │   ├── rental_search_service.py
        │   ├── outreach_service.py
        │   └── lease_service.py
        ├── api/                       # FastAPI routers
        │   ├── __init__.py
        │   ├── dependencies.py       # FastAPI Depends() — auth, db sessions
        │   ├── middleware.py         # Rate limiting, request ID, CORS
        │   ├── routers/
        │   │   ├── searches.py
        │   │   ├── listings.py
        │   │   ├── approvals.py
        │   │   └── leases.py
        │   └── schemas/              # API request/response schemas (NOT domain models)
        │       ├── searches.py
        │       ├── listings.py
        │       └── leases.py
        └── infrastructure/
            ├── __init__.py
            ├── database.py           # Async SQLAlchemy engine + session factory
            ├── cache.py              # Redis client factory
            ├── storage.py            # S3 client
            └── event_store.py        # Event sourcing log writer
```

---

## 4. PHASE 1 — DOMAIN MODELS

**File: `src/defrosted/domain/value_objects.py`**

Write these exact value objects. They are immutable (frozen Pydantic models).
They validate on construction — fail loudly if invalid.

```python
"""
Value objects for the Defrosted domain.

Value objects are immutable. Two value objects with the same data are equal.
They validate themselves on construction — never pass raw strings where a
typed value object is expected.

Karpathy rule: no magic validators. Every validation is an explicit if/raise.
"""
from __future__ import annotations
from decimal import Decimal
import re
from pydantic import BaseModel, model_validator


class Money(BaseModel):
    """
    Represents a monetary amount in USD cents to avoid float arithmetic.

    We store cents as integers because:
        Decimal("1850.00") * Decimal("12") is fine
        1850.0 * 12 = 22199.999999... is not

    Example:
        rent = Money(cents=185000)  # $1,850.00
        rent.dollars  # Decimal("1850.00")
    """
    model_config = {"frozen": True}

    cents: int  # always in USD cents, always positive

    @model_validator(mode="after")
    def cents_must_be_positive(self) -> "Money":
        if self.cents <= 0:
            raise ValueError(
                f"Money.cents must be positive, got {self.cents}. "
                "Use Money(cents=185000) for $1,850.00."
            )
        return self

    @property
    def dollars(self) -> Decimal:
        return Decimal(self.cents) / 100

    @classmethod
    def from_dollars(cls, dollars: Decimal | float | int) -> "Money":
        cents = int(Decimal(str(dollars)) * 100)
        return cls(cents=cents)

    def __add__(self, other: "Money") -> "Money":
        return Money(cents=self.cents + other.cents)

    def __lt__(self, other: "Money") -> bool:
        return self.cents < other.cents

    def __repr__(self) -> str:
        return f"Money(${self.dollars:.2f})"


class Address(BaseModel):
    """
    A US postal address.
    PostGIS coordinates are stored separately in the Listing entity.
    """
    model_config = {"frozen": True}

    street: str
    unit: str | None = None      # apartment number, if any
    city: str
    state: str                   # 2-letter code: "CA", "NY"
    zip_code: str

    @model_validator(mode="after")
    def validate_fields(self) -> "Address":
        if not re.match(r"^[A-Z]{2}$", self.state.upper()):
            raise ValueError(
                f"Address.state must be a 2-letter US state code, got '{self.state}'"
            )
        if not re.match(r"^\d{5}(-\d{4})?$", self.zip_code):
            raise ValueError(
                f"Address.zip_code must be 5-digit or ZIP+4 format, got '{self.zip_code}'"
            )
        return self

    @property
    def full_address(self) -> str:
        unit_part = f" #{self.unit}" if self.unit else ""
        return f"{self.street}{unit_part}, {self.city}, {self.state} {self.zip_code}"


class PhoneNumber(BaseModel):
    """
    E.164 formatted phone number for Twilio and Bland.ai calls.
    Always store normalized — never store raw user input.
    """
    model_config = {"frozen": True}

    e164: str  # e.g. "+14155552671"

    @model_validator(mode="after")
    def must_be_e164(self) -> "PhoneNumber":
        if not re.match(r"^\+[1-9]\d{1,14}$", self.e164):
            raise ValueError(
                f"PhoneNumber must be E.164 format (e.g. '+14155552671'), got '{self.e164}'"
            )
        return self

    @classmethod
    def from_us_number(cls, raw: str) -> "PhoneNumber":
        """
        Parse a US phone number in any common format to E.164.
        Raises ValueError if parsing fails — never returns None.
        """
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 10:
            return cls(e164=f"+1{digits}")
        if len(digits) == 11 and digits[0] == "1":
            return cls(e164=f"+{digits}")
        raise ValueError(
            f"Cannot parse '{raw}' as a US phone number. "
            f"Expected 10 digits (or 11 with country code 1), got {len(digits)} digits."
        )
```

---

**File: `src/defrosted/domain/models.py`**

Write these exact domain entities. Each is a rich model — it carries behavior,
not just data. Use Pydantic v2 throughout.

```python
"""
Core domain entities for Defrosted.

These are the central objects of the system. Everything else serves them.

Design decisions:
- UUIDs for all IDs (never auto-increment integers — they leak user counts
  and are harder to shard later)
- created_at / updated_at on every entity (immutable audit)
- Status fields use Python Enum — never raw strings
- No SQLAlchemy in this file — domain models are pure Python

Karpathy rule: no magic. Every field has an explicit type and default.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from .value_objects import Money, Address, PhoneNumber


# ---------------------------------------------------------------------------
# STATUS ENUMS — explicit state machines, transitions enforced in services
# ---------------------------------------------------------------------------

class SearchStatus(str, Enum):
    PENDING    = "pending"      # user submitted requirements, not started
    SEARCHING  = "searching"    # agent actively scraping listings
    OUTREACHING = "outreaching" # agent contacting landlords
    AWAITING_APPROVAL = "awaiting_approval"  # user needs to pick an option
    APPROVED   = "approved"     # user selected a listing
    SIGNING    = "signing"      # lease coordination in progress
    COMPLETED  = "completed"    # lease signed, move-in confirmed
    FAILED     = "failed"       # terminal failure, needs human review


class ListingSource(str, Enum):
    ZILLOW      = "zillow"
    CRAIGSLIST  = "craigslist"
    FACEBOOK    = "facebook_marketplace"
    HOTPADS     = "hotpads"
    MANUAL      = "manual"       # landlord reached out directly


class ListingStatus(str, Enum):
    ACTIVE      = "active"
    CONTACTED   = "contacted"    # agent sent initial outreach
    RESPONDED   = "responded"    # landlord replied
    TOURING     = "touring"      # tour scheduled
    OFFER_SENT  = "offer_sent"
    ACCEPTED    = "accepted"
    REJECTED    = "rejected"
    UNAVAILABLE = "unavailable"  # listing taken or fake
    GHOST       = "ghost"        # no response after max_followup_attempts


class OutreachChannel(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    SMS   = "sms"
    SOCIAL_DM = "social_dm"


class ApprovalStatus(str, Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED  = "expired"     # user didn't respond within 48h


# ---------------------------------------------------------------------------
# CORE ENTITIES
# ---------------------------------------------------------------------------

class RentalRequirements(BaseModel):
    """
    Structured requirements extracted from the user's natural-language input.
    The LLM parses the user's message into this schema.
    If a field is None, it means the user did not specify — do not filter on it.
    """
    model_config = {"frozen": True}

    city: str
    neighborhoods: list[str] = Field(default_factory=list)
    max_monthly_rent: Money
    min_monthly_rent: Money | None = None
    bedrooms: int | None = None       # None = any
    bathrooms: float | None = None    # None = any; 1.5 means 1 full + 1 half
    move_in_date: datetime
    lease_duration_months: int        # 1–12 for short-term, 12+ for standard
    pets_allowed: bool | None = None  # None = no preference
    parking_required: bool = False
    utilities_included: bool | None = None
    furnished: bool | None = None
    max_commute_minutes: int | None = None
    commute_destination: str | None = None  # e.g. "1 Hacker Way, Menlo Park"
    additional_notes: str | None = None


class RentalSearch(BaseModel):
    """
    The central aggregate root. One RentalSearch per user housing hunt.
    Everything — listings found, outreach attempts, approvals — belongs to it.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    requirements: RentalRequirements
    status: SearchStatus = SearchStatus.PENDING
    temporal_workflow_id: str | None = None   # set when workflow starts
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    failure_reason: str | None = None         # populated on FAILED status

    def is_terminal(self) -> bool:
        """Returns True if this search has reached a final, non-recoverable state."""
        return self.status in (SearchStatus.COMPLETED, SearchStatus.FAILED)

    def can_transition_to(self, new_status: SearchStatus) -> bool:
        """
        Explicit state machine transitions. Only allowed paths:
        PENDING → SEARCHING → OUTREACHING → AWAITING_APPROVAL → APPROVED → SIGNING → COMPLETED
        Any state → FAILED
        """
        allowed: dict[SearchStatus, set[SearchStatus]] = {
            SearchStatus.PENDING:           {SearchStatus.SEARCHING},
            SearchStatus.SEARCHING:         {SearchStatus.OUTREACHING, SearchStatus.FAILED},
            SearchStatus.OUTREACHING:       {SearchStatus.AWAITING_APPROVAL, SearchStatus.FAILED},
            SearchStatus.AWAITING_APPROVAL: {SearchStatus.APPROVED, SearchStatus.FAILED},
            SearchStatus.APPROVED:          {SearchStatus.SIGNING, SearchStatus.FAILED},
            SearchStatus.SIGNING:           {SearchStatus.COMPLETED, SearchStatus.FAILED},
            SearchStatus.COMPLETED:         set(),
            SearchStatus.FAILED:            set(),
        }
        return new_status in allowed.get(self.status, set())


class Landlord(BaseModel):
    """
    A landlord discovered during a rental search.
    We build a profile over time: response rate, ghosting history, preferred contact channel.
    This data becomes the moat — after 10K searches we know more about landlord behavior
    than any human broker ever has.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str | None = None
    email: str | None = None
    phone: PhoneNumber | None = None
    social_handle: str | None = None  # e.g. "@name on Facebook"

    # Behavioral metrics — updated after every interaction
    total_contacts: int = 0
    total_responses: int = 0
    total_ghosts: int = 0              # contacted but never responded
    avg_response_hours: float | None = None
    preferred_contact_channel: OutreachChannel | None = None  # learned from history

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def response_rate(self) -> float | None:
        """
        Response rate as a float 0.0–1.0. None if never contacted.
        Used by the agent to decide which channel to try first.
        """
        if self.total_contacts == 0:
            return None
        return self.total_responses / self.total_contacts


class Listing(BaseModel):
    """
    A rental unit discovered by the browser agent.
    Deduplication is by (source, source_listing_id) — the same unit may appear
    on multiple platforms and must be deduplicated before outreach.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    rental_search_id: uuid.UUID
    landlord_id: uuid.UUID | None = None      # linked after landlord lookup

    source: ListingSource
    source_listing_id: str                     # the platform's own ID
    source_url: str

    address: Address
    latitude: float | None = None             # from PostGIS geocoding
    longitude: float | None = None

    monthly_rent: Money
    bedrooms: int | None = None
    bathrooms: float | None = None
    square_feet: int | None = None
    available_date: datetime | None = None
    lease_duration_months: int | None = None
    pets_allowed: bool | None = None
    parking_included: bool | None = None
    utilities_included: bool | None = None
    furnished: bool | None = None
    description: str | None = None
    photos: list[str] = Field(default_factory=list)  # S3 URLs

    status: ListingStatus = ListingStatus.ACTIVE
    is_duplicate: bool = False                 # flagged by dedup algorithm
    dedup_canonical_id: uuid.UUID | None = None  # points to the canonical listing

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OutreachAttempt(BaseModel):
    """
    A single contact attempt to a landlord for a specific listing.
    Every attempt is recorded — this is the source of truth for what the agent
    has done. The user can see this log in their dashboard.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    rental_search_id: uuid.UUID
    listing_id: uuid.UUID
    landlord_id: uuid.UUID

    channel: OutreachChannel
    direction: str = "outbound"          # "outbound" | "inbound"
    message_body: str
    subject: str | None = None           # for email

    # External provider references — for verification and audit
    sendgrid_message_id: str | None = None
    twilio_sid: str | None = None
    bland_call_id: str | None = None

    # Set when landlord responds
    response_body: str | None = None
    responded_at: datetime | None = None
    response_sentiment: str | None = None  # "positive" | "negative" | "neutral"

    attempt_number: int = 1              # 1 = first contact, 2+ = follow-up
    sent_at: datetime = Field(default_factory=datetime.utcnow)

    def is_response_overdue(self, timeout_hours: int = 48) -> bool:
        """
        Returns True if we sent this outreach more than timeout_hours ago
        and have not received a response.
        """
        if self.responded_at is not None:
            return False   # already responded
        hours_elapsed = (datetime.utcnow() - self.sent_at).total_seconds() / 3600
        return hours_elapsed > timeout_hours


class HumanApproval(BaseModel):
    """
    A decision point where the user must approve before the agent proceeds.
    Used for: selecting a listing, confirming an offer amount, signing a lease.

    The agent STOPS at every HumanApproval and waits for a Temporal signal.
    It never proceeds autonomously past these gates.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    rental_search_id: uuid.UUID
    listing_id: uuid.UUID | None = None

    approval_type: str              # "listing_selection" | "offer_confirmation" | "lease_signing"
    prompt_shown_to_user: str       # the question displayed to the user
    options: list[dict[str, Any]]   # structured options for the user to choose from

    status: ApprovalStatus = ApprovalStatus.PENDING
    user_choice: dict[str, Any] | None = None   # what the user selected
    user_note: str | None = None                # optional free-text from user

    expires_at: datetime           # if user doesn't respond, status → EXPIRED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    decided_at: datetime | None = None


class Lease(BaseModel):
    """
    The final artifact. Created when a landlord accepts and the user approves.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    rental_search_id: uuid.UUID
    listing_id: uuid.UUID
    landlord_id: uuid.UUID
    user_id: uuid.UUID

    monthly_rent: Money
    move_in_date: datetime
    lease_duration_months: int
    address: Address

    # Document references
    lease_document_s3_key: str | None = None    # original landlord PDF
    signed_document_s3_key: str | None = None   # after e-signature
    docusign_envelope_id: str | None = None

    signed_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

**File: `src/defrosted/domain/events.py`**

```python
"""
Domain events for the Defrosted event store.

Every consequential action in the system emits an event. These events are:
- Immutable: once written, never modified
- Ordered: monotonically increasing sequence per rental_search_id
- Complete: the full state of a search can be reconstructed from its events

Why event sourcing matters for Defrosted:
When an AI agent submits an offer on a $2,000/month apartment on behalf of a user,
you need an immutable record of:
  - Who authorized what
  - What the agent did and when
  - What the LLM was given as context
  - What the external system (SendGrid, Bland) confirmed
This is your legal protection, your audit trail, and your debugging tool.

Karpathy rule: events are data, not behavior. No methods that mutate state.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """
    Every event shares these fields.
    event_id: globally unique across all events
    sequence: monotonically increasing per rental_search_id (for ordering)
    """
    model_config = {"frozen": True}

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    rental_search_id: uuid.UUID
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    sequence: int  # assigned by the event store, not by the caller


class SearchStartedEvent(BaseEvent):
    event_type: Literal["search_started"] = "search_started"
    user_id: uuid.UUID
    requirements_snapshot: dict[str, Any]   # JSON snapshot of requirements at start time


class ListingDiscoveredEvent(BaseEvent):
    event_type: Literal["listing_discovered"] = "listing_discovered"
    listing_id: uuid.UUID
    source: str
    source_url: str
    monthly_rent_cents: int


class DuplicateListingFlaggedEvent(BaseEvent):
    event_type: Literal["duplicate_listing_flagged"] = "duplicate_listing_flagged"
    duplicate_listing_id: uuid.UUID
    canonical_listing_id: uuid.UUID
    dedup_reason: str    # e.g. "same address + same rent within 5% + same photos hash"


class OutreachSentEvent(BaseEvent):
    event_type: Literal["outreach_sent"] = "outreach_sent"
    outreach_attempt_id: uuid.UUID
    listing_id: uuid.UUID
    landlord_id: uuid.UUID
    channel: str
    # The VERIFIED confirmation from the external provider (never LLM self-report)
    provider_message_id: str        # SendGrid message ID, Twilio SID, or Bland call ID
    verified_sent_at: datetime      # timestamp from provider API, not our system clock


class LandlordRespondedEvent(BaseEvent):
    event_type: Literal["landlord_responded"] = "landlord_responded"
    outreach_attempt_id: uuid.UUID
    listing_id: uuid.UUID
    landlord_id: uuid.UUID
    channel: str
    response_sentiment: str         # "positive" | "negative" | "neutral"
    hours_to_response: float


class LandlordGhostedEvent(BaseEvent):
    event_type: Literal["landlord_ghosted"] = "landlord_ghosted"
    listing_id: uuid.UUID
    landlord_id: uuid.UUID
    total_attempts: int
    last_channel_tried: str


class UserApprovalRequestedEvent(BaseEvent):
    event_type: Literal["user_approval_requested"] = "user_approval_requested"
    approval_id: uuid.UUID
    approval_type: str
    options_count: int


class UserApprovedListingEvent(BaseEvent):
    event_type: Literal["user_approved_listing"] = "user_approved_listing"
    approval_id: uuid.UUID
    listing_id: uuid.UUID
    approved_monthly_rent_cents: int


class OfferSubmittedEvent(BaseEvent):
    event_type: Literal["offer_submitted"] = "offer_submitted"
    listing_id: uuid.UUID
    landlord_id: uuid.UUID
    offered_rent_cents: int
    move_in_date: datetime
    submitted_via: str    # "email" | "phone" | "sms"
    user_authorized: bool = True   # always True — we require approval before offer


class LeaseSignedEvent(BaseEvent):
    event_type: Literal["lease_signed"] = "lease_signed"
    lease_id: uuid.UUID
    listing_id: uuid.UUID
    signed_document_s3_key: str
    docusign_envelope_id: str
    monthly_rent_cents: int
    move_in_date: datetime


# Union type for the event store — add every new event type here
DomainEvent = (
    SearchStartedEvent
    | ListingDiscoveredEvent
    | DuplicateListingFlaggedEvent
    | OutreachSentEvent
    | LandlordRespondedEvent
    | LandlordGhostedEvent
    | UserApprovalRequestedEvent
    | UserApprovedListingEvent
    | OfferSubmittedEvent
    | LeaseSignedEvent
)
```

---

## 5. PHASE 2 — REPOSITORY LAYER

**File: `src/defrosted/repositories/base.py`**

```python
"""
Base repository pattern.

Repositories are the ONLY way to talk to the database.
Services never write SQL. They call repository methods.
This makes testing trivial (swap DB for in-memory dict) and
keeps all SQL in one predictable place.

Karpathy rule: every method is explicit. No magic query builders.
The SQL should be readable by a human, not generated by 5 layers of ORM magic.
"""
from __future__ import annotations
import uuid
from typing import TypeVar, Generic, Type
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """
    Generic base. Subclasses define their model type.

    Usage:
        class ListingRepository(BaseRepository[Listing]):
            model_class = Listing
            ...
    """
    model_class: Type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        # The session is injected — the repository never creates its own session.
        # This enables transactional consistency: multiple repos in one request
        # share the same session and commit/rollback together.
        self.session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> ModelT | None:
        raise NotImplementedError(
            f"{self.__class__.__name__}.get_by_id() must be implemented"
        )

    async def save(self, entity: ModelT) -> ModelT:
        raise NotImplementedError(
            f"{self.__class__.__name__}.save() must be implemented"
        )

    async def delete(self, entity_id: uuid.UUID) -> bool:
        raise NotImplementedError(
            f"{self.__class__.__name__}.delete() must be implemented"
        )
```

**File: `src/defrosted/repositories/listing_repository.py`**

```python
"""
Listing repository.

Key algorithms:
1. Geospatial search (PostGIS): find listings within radius of a point
2. Deduplication: identify listings that are the same unit on different platforms

Deduplication algorithm:
  A listing is a duplicate of an existing listing if ALL of these are true:
  - Same city (normalized to lowercase)
  - Same street address (normalized: lowercase, remove "St" vs "Street", etc.)
  - Same monthly rent within 5% tolerance (landlords sometimes list $1,800 on
    Zillow and $1,795 on Craigslist — same unit)
  - Move-in date within 30 days of each other
  OR:
  - Same listing photos (phash comparison) — strongest signal

  When a duplicate is found:
  - Keep the listing with the most complete data as the canonical
  - Flag the other as duplicate, point to canonical
  - Emit DuplicateListingFlaggedEvent
  - Only contact the landlord ONCE (via the canonical listing)

Karpathy rule: the dedup logic is in this file, not scattered across the codebase.
"""
from __future__ import annotations
import uuid
from decimal import Decimal
from difflib import SequenceMatcher
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..domain.models import Listing, ListingStatus
from ..domain.value_objects import Money
from .base import BaseRepository


class ListingRepository(BaseRepository[Listing]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_id(self, listing_id: uuid.UUID) -> Listing | None:
        result = await self.session.execute(
            text("SELECT * FROM listings WHERE id = :id"),
            {"id": str(listing_id)},
        )
        row = result.mappings().first()
        return Listing(**row) if row else None

    async def get_by_source_id(
        self, source: str, source_listing_id: str
    ) -> Listing | None:
        """
        Check if we already have this listing from this platform.
        Used during ingestion to avoid re-processing the same listing.
        """
        result = await self.session.execute(
            text("""
                SELECT * FROM listings
                WHERE source = :source
                  AND source_listing_id = :source_listing_id
                LIMIT 1
            """),
            {"source": source, "source_listing_id": source_listing_id},
        )
        row = result.mappings().first()
        return Listing(**row) if row else None

    async def find_within_radius_km(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        rental_search_id: uuid.UUID,
    ) -> list[Listing]:
        """
        PostGIS geospatial query: find all active, non-duplicate listings for this
        search within radius_km kilometers of the given coordinates.

        Uses ST_DWithin with geography type for accurate distance in meters.
        radius_km * 1000 converts to meters (ST_DWithin uses meters for geography).
        """
        result = await self.session.execute(
            text("""
                SELECT * FROM listings
                WHERE rental_search_id = :search_id
                  AND status != 'unavailable'
                  AND is_duplicate = false
                  AND ST_DWithin(
                      location::geography,
                      ST_MakePoint(:lng, :lat)::geography,
                      :radius_meters
                  )
                ORDER BY monthly_rent_cents ASC
            """),
            {
                "search_id": str(rental_search_id),
                "lat": latitude,
                "lng": longitude,
                "radius_meters": radius_km * 1000,
            },
        )
        return [Listing(**row) for row in result.mappings().all()]

    async def find_duplicate_candidate(self, listing: Listing) -> Listing | None:
        """
        Find an existing listing that is likely the same unit as the given listing.
        Returns the canonical listing if a duplicate is found, None otherwise.

        This is called during listing ingestion before saving.
        See module docstring for the deduplication algorithm.
        """
        if listing.latitude is None or listing.longitude is None:
            # Can't do geo-based dedup without coordinates — fall back to address string match
            return await self._find_duplicate_by_address(listing)

        # Step 1: find listings within 50 meters (same building) with similar rent
        rent_floor = int(listing.monthly_rent.cents * 0.95)
        rent_ceil  = int(listing.monthly_rent.cents * 1.05)

        result = await self.session.execute(
            text("""
                SELECT * FROM listings
                WHERE id != :id
                  AND is_duplicate = false
                  AND monthly_rent_cents BETWEEN :rent_floor AND :rent_ceil
                  AND ST_DWithin(
                      location::geography,
                      ST_MakePoint(:lng, :lat)::geography,
                      50  -- 50 meters — same building
                  )
                LIMIT 5
            """),
            {
                "id": str(listing.id),
                "rent_floor": rent_floor,
                "rent_ceil": rent_ceil,
                "lat": listing.latitude,
                "lng": listing.longitude,
            },
        )
        candidates = [Listing(**row) for row in result.mappings().all()]

        for candidate in candidates:
            if self._is_same_unit(listing, candidate):
                return candidate

        return None

    def _is_same_unit(self, a: Listing, b: Listing) -> bool:
        """
        Returns True if listing a and listing b are the same physical unit.
        Uses address string similarity as the tiebreaker after geo proximity + rent check.
        """
        address_similarity = SequenceMatcher(
            None,
            a.address.full_address.lower(),
            b.address.full_address.lower(),
        ).ratio()

        # 0.8 threshold: "123 Main St Apt 2" vs "123 Main Street #2" = ~0.85
        return address_similarity > 0.8

    async def _find_duplicate_by_address(self, listing: Listing) -> Listing | None:
        """
        Fallback dedup when we don't have coordinates.
        Uses normalized address string matching in Postgres.
        """
        result = await self.session.execute(
            text("""
                SELECT * FROM listings
                WHERE id != :id
                  AND is_duplicate = false
                  AND city = :city
                  AND zip_code = :zip_code
                  AND monthly_rent_cents BETWEEN :rent_floor AND :rent_ceil
                LIMIT 10
            """),
            {
                "id": str(listing.id),
                "city": listing.address.city.lower(),
                "zip_code": listing.address.zip_code,
                "rent_floor": int(listing.monthly_rent.cents * 0.95),
                "rent_ceil":  int(listing.monthly_rent.cents * 1.05),
            },
        )
        candidates = [Listing(**row) for row in result.mappings().all()]
        for candidate in candidates:
            if self._is_same_unit(listing, candidate):
                return candidate
        return None

    async def save(self, listing: Listing) -> Listing:
        await self.session.execute(
            text("""
                INSERT INTO listings (
                    id, rental_search_id, landlord_id, source, source_listing_id,
                    source_url, street, unit, city, state, zip_code,
                    latitude, longitude, monthly_rent_cents,
                    bedrooms, bathrooms, square_feet, available_date,
                    lease_duration_months, pets_allowed, parking_included,
                    utilities_included, furnished, description, photos,
                    status, is_duplicate, dedup_canonical_id,
                    created_at, updated_at
                ) VALUES (
                    :id, :rental_search_id, :landlord_id, :source, :source_listing_id,
                    :source_url, :street, :unit, :city, :state, :zip_code,
                    :latitude, :longitude, :monthly_rent_cents,
                    :bedrooms, :bathrooms, :square_feet, :available_date,
                    :lease_duration_months, :pets_allowed, :parking_included,
                    :utilities_included, :furnished, :description, :photos,
                    :status, :is_duplicate, :dedup_canonical_id,
                    :created_at, :updated_at
                )
                ON CONFLICT (source, source_listing_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "id": str(listing.id),
                "rental_search_id": str(listing.rental_search_id),
                "landlord_id": str(listing.landlord_id) if listing.landlord_id else None,
                "source": listing.source.value,
                "source_listing_id": listing.source_listing_id,
                "source_url": listing.source_url,
                "street": listing.address.street,
                "unit": listing.address.unit,
                "city": listing.address.city.lower(),
                "state": listing.address.state.upper(),
                "zip_code": listing.address.zip_code,
                "latitude": listing.latitude,
                "longitude": listing.longitude,
                "monthly_rent_cents": listing.monthly_rent.cents,
                "bedrooms": listing.bedrooms,
                "bathrooms": listing.bathrooms,
                "square_feet": listing.square_feet,
                "available_date": listing.available_date,
                "lease_duration_months": listing.lease_duration_months,
                "pets_allowed": listing.pets_allowed,
                "parking_included": listing.parking_included,
                "utilities_included": listing.utilities_included,
                "furnished": listing.furnished,
                "description": listing.description,
                "photos": listing.photos,
                "status": listing.status.value,
                "is_duplicate": listing.is_duplicate,
                "dedup_canonical_id": str(listing.dedup_canonical_id) if listing.dedup_canonical_id else None,
                "created_at": listing.created_at,
                "updated_at": listing.updated_at,
            }
        )
        return listing
```

---

## 6. PHASE 3 — AGENT TOOLS

**File: `src/defrosted/agents/tools/base.py`**

```python
"""
AgentTool base interface.

Every tool the LLM agent can call implements this interface.
The critical design decision: every tool has a verify() method.

Why verify() is non-negotiable:
  The Replit incident (July 2025) — an AI agent deleted a production database
  and then reported success. It fabricated confirmations. If your agent says
  "I sent the email," you verify it against SendGrid's API before recording
  the action. Never trust the LLM's self-report.

  In this system: the LLM calls a tool → the tool calls the external provider
  → the tool calls verify() against the provider's API → only if verify()
  returns True does the action get recorded as an event in the event store.

Karpathy rule: this interface is small and explicit. 4 methods. That's it.
"""
from __future__ import annotations
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """
    What every tool returns. Success or failure with a clear message.
    provider_reference: the external system's ID for this action
                        (SendGrid message ID, Twilio SID, Bland call ID)
                        Used by verify() to confirm the action happened.
    """
    success: bool
    message: str
    data: dict[str, Any]
    provider_reference: str | None = None   # None if action didn't reach provider


class AgentTool(ABC):
    """
    Every agent tool implements these 4 methods. Nothing more.

    tool_name:  human-readable name for logging and the agent's tool registry
    execute():  call the external provider, return ToolResult
    verify():   call the provider's API to confirm the action happened
                Returns True only if the provider confirms success.
                Called automatically by the orchestrator — tools never skip it.
    describe(): returns the function schema for LLM tool calling
    """

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Unique name used in LLM tool call schemas and log messages."""
        ...

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """
        Execute the action. May succeed or fail — always returns ToolResult.
        Never raises an exception for external failures (provider down, rate limit).
        Raise only for programming errors (missing required param, wrong type).
        """
        ...

    @abstractmethod
    async def verify(self, provider_reference: str) -> bool:
        """
        Confirm with the external provider that the action succeeded.
        Called by the orchestrator AFTER execute() returns success.

        provider_reference: the ID from execute()'s ToolResult.provider_reference
        Returns: True if provider confirms action happened, False otherwise.
        """
        ...

    @abstractmethod
    def describe(self) -> dict[str, Any]:
        """
        Returns the LLM function calling schema for this tool.
        Used by the orchestrator to build the tools list for the Claude API call.
        """
        ...
```

**File: `src/defrosted/agents/tools/email_tool.py`**

```python
"""
Email outreach tool. Sends the initial message and follow-ups to landlords.

Security rules enforced in this file:
1. Never send an email without a HumanApproval record in the DB first.
   (The orchestrator enforces this — this tool double-checks.)
2. Always include the disclosure header: "This message was sent on behalf of
   [User Name] by Defrosted, an AI rental agent."
3. Rate limit: max 30 outreach emails per rental_search_id per 24 hours.
   (Prevents abuse and keeps us off spam blacklists.)
4. Never include PII about the user beyond name and basic requirements.
   (No SSN, income, date of birth — that comes only in the formal application stage.)

Verify() implementation:
  SendGrid's Get Message API returns message status. We poll until:
  - "delivered": success
  - "dropped" | "bounced" | "blocked": failure
  - Timeout after 5 minutes: treat as failure, retry on different channel.
"""
from __future__ import annotations
import asyncio
from typing import Any
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from ..config import Settings
from .base import AgentTool, ToolResult


DISCLOSURE_FOOTER = """
---
This message was sent on behalf of {renter_name} by Defrosted (defrosted.ai),
an AI rental agent. {renter_name} authorized this message on {authorized_at}.
If you have questions, reply to this email or contact support@defrosted.ai.
"""

MAX_EMAILS_PER_SEARCH_PER_DAY = 30


class EmailOutreachTool(AgentTool):

    def __init__(self, settings: Settings, rate_limiter: "RateLimiter") -> None:
        self._client = SendGridAPIClient(api_key=settings.sendgrid_api_key)
        self._rate_limiter = rate_limiter
        self._from_email = settings.outreach_from_email   # e.g. "agent@defrosted.ai"

    @property
    def tool_name(self) -> str:
        return "email_landlord"

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """
        Required params:
          rental_search_id: str
          landlord_email: str
          renter_name: str
          authorized_at: str (ISO datetime)
          subject: str
          body: str
          attempt_number: int (1 = first contact, 2+ = follow-up)
        """
        # Validate required params explicitly — fail loudly
        required = ["rental_search_id", "landlord_email", "renter_name",
                    "authorized_at", "subject", "body", "attempt_number"]
        missing = [k for k in required if k not in params]
        if missing:
            raise ValueError(
                f"EmailOutreachTool.execute() missing required params: {missing}. "
                f"Got: {list(params.keys())}"
            )

        # Rate limit check — prevent spam
        rate_key = f"email_outreach:{params['rental_search_id']}"
        current_count = await self._rate_limiter.get_count(rate_key)
        if current_count >= MAX_EMAILS_PER_SEARCH_PER_DAY:
            return ToolResult(
                success=False,
                message=(
                    f"Rate limit reached: {current_count} emails sent today for "
                    f"search {params['rental_search_id']}. Max is {MAX_EMAILS_PER_SEARCH_PER_DAY}."
                ),
                data={"rate_limited": True},
                provider_reference=None,
            )

        # Append mandatory disclosure footer
        full_body = params["body"] + DISCLOSURE_FOOTER.format(
            renter_name=params["renter_name"],
            authorized_at=params["authorized_at"],
        )

        message = Mail(
            from_email=self._from_email,
            to_emails=params["landlord_email"],
            subject=params["subject"],
            plain_text_content=full_body,
        )

        try:
            response = self._client.send(message)
        except Exception as exc:
            # External provider error — log and return failure, don't raise
            return ToolResult(
                success=False,
                message=f"SendGrid API error: {exc}",
                data={"error": str(exc)},
                provider_reference=None,
            )

        if response.status_code not in (200, 202):
            return ToolResult(
                success=False,
                message=f"SendGrid rejected message: HTTP {response.status_code}",
                data={"status_code": response.status_code, "body": response.body},
                provider_reference=None,
            )

        # SendGrid message ID is in the X-Message-Id header
        message_id = response.headers.get("X-Message-Id")
        if not message_id:
            # SendGrid should always return this — if it doesn't, something is wrong
            return ToolResult(
                success=False,
                message="SendGrid returned 202 but no X-Message-Id header. Cannot verify.",
                data={"headers": dict(response.headers)},
                provider_reference=None,
            )

        await self._rate_limiter.increment(rate_key, ttl_seconds=86400)

        return ToolResult(
            success=True,
            message=f"Email queued with SendGrid. Message ID: {message_id}",
            data={"to": params["landlord_email"], "subject": params["subject"]},
            provider_reference=message_id,
        )

    async def verify(self, provider_reference: str) -> bool:
        """
        Poll SendGrid's Message Activity API to confirm delivery.
        Retries up to 5 times with 60s interval (max 5 minutes wait).
        Returns True only on "delivered". Returns False on any other terminal state.
        """
        terminal_success = {"delivered"}
        terminal_failure = {"dropped", "bounced", "blocked", "unsubscribed",
                            "spam_report", "invalid"}
        max_attempts = 5
        poll_interval_seconds = 60

        for attempt in range(max_attempts):
            try:
                response = self._client.client.messages._(provider_reference).get()
                events = response.to_dict().get("messages", [])
                if not events:
                    await asyncio.sleep(poll_interval_seconds)
                    continue

                latest_event = events[-1].get("status", "")
                if latest_event in terminal_success:
                    return True
                if latest_event in terminal_failure:
                    return False

            except Exception:
                pass  # transient API error — retry

            await asyncio.sleep(poll_interval_seconds)

        # Timed out — could not confirm delivery
        return False

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.tool_name,
            "description": (
                "Send an email to a landlord on behalf of the renter. "
                "Use for initial outreach and follow-ups. "
                "Always include the landlord's name if known. "
                "Be professional and concise — under 150 words."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "landlord_email": {"type": "string", "description": "Landlord's email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body. Under 150 words. Professional tone."},
                    "attempt_number": {"type": "integer", "description": "1 for first contact, 2+ for follow-up"},
                },
                "required": ["landlord_email", "subject", "body", "attempt_number"],
            },
        }
```

---

## 7. PHASE 4 — TEMPORAL WORKFLOW

**File: `src/defrosted/workflows/rental_search_workflow.py`**

```python
"""
Temporal workflow for a complete rental search.

Why Temporal and not a cron job or Celery task:
A rental search takes hours to days:
  - Browser scraping: 10–30 minutes to collect 50+ listings
  - Landlord outreach: send email, wait 48 hours, follow up, wait 24 more hours
  - Lease signing: wait for DocuSign to complete

Temporal gives us:
  1. Durable execution: if the server crashes at hour 23, the workflow resumes exactly
     where it left off when the server restarts. Zero data loss.
  2. Signals: the workflow pauses at human approval gates and waits for a signal
     (the user's approval) before continuing. Clean and explicit.
  3. Timeouts: each activity has a start-to-close timeout. If an activity hangs,
     Temporal handles the retry logic.
  4. Visibility: every workflow step is visible in the Temporal Web UI with full history.

Architecture:
  - The workflow is the coordinator: it calls activities in sequence.
  - Activities are the workers: each does one thing (scrape, email, verify, etc.)
  - Activities are retryable: Temporal retries failed activities with backoff.
  - The workflow itself is NOT retried: it runs to completion or fails terminally.

Karpathy rule: the workflow reads like a recipe. Top to bottom. No magic.
"""
from __future__ import annotations
import uuid
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities — each activity is a simple async function, not a class
from ..activities import (
    scrape_listings_activity,
    deduplicate_listings_activity,
    contact_landlords_activity,
    wait_for_responses_activity,
    build_approval_options_activity,
    submit_offer_activity,
    coordinate_lease_activity,
)


@workflow.defn
class RentalSearchWorkflow:
    """
    Top-level workflow for one renter's housing search.

    Signals (external → workflow):
        user_approved_listing: called when the user selects a listing in the UI

    Queries (read-only, from external):
        get_status: returns current workflow status and progress
    """

    def __init__(self) -> None:
        # Approval signal — set when user approves a listing
        # None = no approval received yet
        self._user_approval: dict | None = None

    @workflow.signal
    def user_approved_listing(self, approval_data: dict) -> None:
        """
        Called by the API when the user selects a listing.
        The workflow is blocking at the approval gate and will resume when this fires.
        """
        self._user_approval = approval_data

    @workflow.query
    def get_status(self) -> dict:
        """Read-only snapshot of current workflow state for the UI."""
        return {
            "has_approval": self._user_approval is not None,
            "approval": self._user_approval,
        }

    @workflow.run
    async def run(self, rental_search_id: str) -> dict:
        """
        The complete rental search pipeline. Reads top to bottom.
        Each step is an activity call with explicit timeout and retry policy.
        """
        search_id = uuid.UUID(rental_search_id)

        # ── Step 1: Scrape listings ──────────────────────────────────────────
        # Scraping can take 10–30 minutes. Max 2 retries if it fails.
        listings = await workflow.execute_activity(
            scrape_listings_activity,
            args=[rental_search_id],
            start_to_close_timeout=timedelta(minutes=45),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(minutes=2),
            ),
        )

        if not listings:
            return {"status": "failed", "reason": "no_listings_found"}

        # ── Step 2: Deduplicate ──────────────────────────────────────────────
        unique_listings = await workflow.execute_activity(
            deduplicate_listings_activity,
            args=[rental_search_id, listings],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        # ── Step 3: Contact landlords ────────────────────────────────────────
        # Sends initial outreach to up to 20 unique listings.
        # Returns list of outreach_attempt_ids.
        outreach_results = await workflow.execute_activity(
            contact_landlords_activity,
            args=[rental_search_id, unique_listings],
            start_to_close_timeout=timedelta(hours=2),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        # ── Step 4: Wait for responses ───────────────────────────────────────
        # Poll for landlord responses over 48–72 hours.
        # Sends follow-ups at 24h and 48h if no response.
        # Returns list of listings with confirmed interest from landlord.
        confirmed_listings = await workflow.execute_activity(
            wait_for_responses_activity,
            args=[rental_search_id, outreach_results],
            start_to_close_timeout=timedelta(hours=96),   # up to 4 days
            retry_policy=RetryPolicy(maximum_attempts=1),  # no retry on this one
        )

        if not confirmed_listings:
            return {"status": "failed", "reason": "no_landlord_responses"}

        # ── Step 5: Build approval options and wait for user ─────────────────
        # Present top 3–5 listings to the user.
        # Block here until user_approved_listing signal fires (or 48h timeout).
        approval_options = await workflow.execute_activity(
            build_approval_options_activity,
            args=[rental_search_id, confirmed_listings],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        # Wait for the human signal — with 48-hour timeout
        await workflow.wait_condition(
            lambda: self._user_approval is not None,
            timeout=timedelta(hours=48),
        )

        if self._user_approval is None:
            # Timed out — user didn't respond
            return {"status": "failed", "reason": "approval_timeout"}

        selected_listing_id = self._user_approval["listing_id"]

        # ── Step 6: Submit offer ─────────────────────────────────────────────
        offer_result = await workflow.execute_activity(
            submit_offer_activity,
            args=[rental_search_id, selected_listing_id, self._user_approval],
            start_to_close_timeout=timedelta(hours=4),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        if not offer_result["accepted"]:
            return {"status": "failed", "reason": "offer_rejected", "details": offer_result}

        # ── Step 7: Coordinate lease ─────────────────────────────────────────
        lease_result = await workflow.execute_activity(
            coordinate_lease_activity,
            args=[rental_search_id, selected_listing_id, offer_result],
            start_to_close_timeout=timedelta(hours=48),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        return {
            "status": "completed",
            "lease_id": lease_result["lease_id"],
            "listing_id": selected_listing_id,
            "signed_at": lease_result["signed_at"],
        }
```

---

## 8. PHASE 5 — API LAYER

**File: `src/defrosted/api/routers/searches.py`**

```python
"""
REST API for rental searches.

Security applied at this layer:
1. Every endpoint requires a valid JWT (via Depends(get_current_user))
2. Users can only access their own searches (ownership check on every endpoint)
3. Rate limiting on search creation: max 3 active searches per user
4. Input validation: Pydantic schemas for every request body
5. No internal IDs in error messages (don't tell the user what table we use)

Karpathy rule: the route handler is thin. Business logic lives in the service layer.
The handler: validate input → call service → return response. That's it.
"""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from ..dependencies import get_current_user, get_db_session, get_rental_search_service
from ..schemas.searches import (
    CreateSearchRequest,
    SearchResponse,
    SearchListResponse,
)
from ...domain.models import SearchStatus
from ...services.rental_search_service import RentalSearchService

router = APIRouter(prefix="/searches", tags=["rental-searches"])


@router.post(
    "/",
    response_model=SearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new rental search",
    description=(
        "Parses the renter's natural language requirements, creates a search record, "
        "and starts the Temporal workflow. Returns immediately — the search runs async."
    ),
)
async def create_search(
    body: CreateSearchRequest,
    current_user: dict = Depends(get_current_user),
    service: RentalSearchService = Depends(get_rental_search_service),
) -> SearchResponse:
    user_id = uuid.UUID(current_user["sub"])

    # Service enforces: max 3 active searches per user
    search = await service.create_search(
        user_id=user_id,
        raw_requirements=body.requirements_text,
    )
    return SearchResponse.from_domain(search)


@router.get(
    "/{search_id}",
    response_model=SearchResponse,
    summary="Get search status and results",
)
async def get_search(
    search_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    service: RentalSearchService = Depends(get_rental_search_service),
) -> SearchResponse:
    user_id = uuid.UUID(current_user["sub"])

    search = await service.get_search(search_id=search_id)
    if search is None:
        # Use 404 for both "not found" and "not yours" — don't leak existence
        raise HTTPException(status_code=404, detail="Search not found")

    if search.user_id != user_id:
        raise HTTPException(status_code=404, detail="Search not found")

    return SearchResponse.from_domain(search)


@router.post(
    "/{search_id}/approve",
    response_model=SearchResponse,
    summary="Approve a listing — unblocks the agent workflow",
    description=(
        "The user selects their preferred listing. This sends a Temporal signal "
        "to the waiting workflow, which then proceeds to submit the offer."
    ),
)
async def approve_listing(
    search_id: uuid.UUID,
    listing_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    service: RentalSearchService = Depends(get_rental_search_service),
) -> SearchResponse:
    user_id = uuid.UUID(current_user["sub"])

    search = await service.get_search(search_id=search_id)
    if search is None or search.user_id != user_id:
        raise HTTPException(status_code=404, detail="Search not found")

    if search.status != SearchStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Search is not awaiting approval. Current status: {search.status.value}",
        )

    updated_search = await service.approve_listing(
        search_id=search_id,
        listing_id=listing_id,
        user_id=user_id,
    )
    return SearchResponse.from_domain(updated_search)
```

---

## 9. PHASE 6 — SECURITY

**File: `src/defrosted/api/middleware.py`**

```python
"""
Security middleware applied to every request.

Layers:
1. Request ID: every request gets a UUID for tracing across logs
2. Rate limiting: per-IP and per-user limits via Redis
3. Security headers: HSTS, X-Frame-Options, CSP, etc.
4. CORS: strict origin allowlist

What this does NOT do (handled elsewhere):
- JWT auth: in Depends(get_current_user) in dependencies.py
- Input validation: in Pydantic schemas in api/schemas/
- Business rule enforcement: in services/

Karpathy rule: middleware is boring on purpose. It should be invisible.
"""
from __future__ import annotations
import time
import uuid
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from ..infrastructure.cache import get_redis_client

log = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request and response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        # Bind to structlog context so every log line in this request includes it
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id

        log.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        # CSP: allow only our own origin and Anthropic/Claude APIs
        "Content-Security-Policy": (
            "default-src 'self'; "
            "connect-src 'self' https://api.anthropic.com; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline';"
        ),
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in self.HEADERS.items():
            response.headers[header] = value
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter using Redis.
    Limits:
      - Per IP:   100 requests per minute (protects against bots)
      - Per user: 1000 requests per minute (authenticated users get higher limit)

    Uses Redis INCR with TTL — atomic, no race conditions.
    """

    IP_LIMIT   = 100   # requests per minute per IP
    USER_LIMIT = 1000  # requests per minute per authenticated user
    WINDOW_SECONDS = 60

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._redis = None   # initialized lazily to avoid startup import issues

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._redis is None:
            self._redis = await get_redis_client()

        client_ip = request.client.host if request.client else "unknown"
        ip_key = f"rate_limit:ip:{client_ip}"

        ip_count = await self._redis.incr(ip_key)
        if ip_count == 1:
            # First request in this window — set the TTL
            await self._redis.expire(ip_key, self.WINDOW_SECONDS)

        if ip_count > self.IP_LIMIT:
            return Response(
                content='{"detail":"Rate limit exceeded. Max 100 requests per minute."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self.WINDOW_SECONDS)},
            )

        return await call_next(request)
```

---

## 10. PHASE 7 — TESTS

Write tests for these exact behaviors. Coverage target is behavior coverage,
not line coverage. A test that tests implementation details is worse than no test.

**File: `tests/unit/domain/test_listing_dedup.py`**

```python
"""
Tests for the listing deduplication algorithm.

We test the BEHAVIOR: given two listings, does the algorithm correctly
identify them as the same unit or different units?

We do NOT test: which internal methods are called, how many SQL queries run,
what the repository's internal state looks like.

Karpathy rule: tests should read like specifications.
"""
import pytest
from defrosted.domain.models import Listing, ListingSource, ListingStatus
from defrosted.domain.value_objects import Money, Address
from defrosted.repositories.listing_repository import ListingRepository
import uuid
from datetime import datetime


def make_listing(
    street: str = "123 Main St",
    city: str = "San Jose",
    state: str = "CA",
    zip_code: str = "95101",
    rent_dollars: float = 1800.0,
    source: ListingSource = ListingSource.ZILLOW,
    source_id: str = "zillow-abc123",
    lat: float = 37.3382,
    lng: float = -121.8863,
) -> Listing:
    """Factory for test listings. Only override what your test cares about."""
    return Listing(
        id=uuid.uuid4(),
        rental_search_id=uuid.uuid4(),
        source=source,
        source_listing_id=source_id,
        source_url=f"https://zillow.com/{source_id}",
        address=Address(street=street, city=city, state=state, zip_code=zip_code),
        monthly_rent=Money.from_dollars(rent_dollars),
        latitude=lat,
        longitude=lng,
    )


class TestListingDeduplication:
    """
    Same physical unit, different platforms → should be flagged as duplicates.
    Different units nearby → should NOT be flagged.
    """

    def test_same_address_same_rent_is_duplicate(self):
        """
        The clearest case: same address, same rent, different platforms.
        This is the most common scenario — a landlord lists on Zillow AND Craigslist.
        """
        repo = ListingRepository(session=None)   # session not needed for unit test

        listing_a = make_listing(
            source=ListingSource.ZILLOW,
            source_id="zillow-abc",
            rent_dollars=1800.0,
        )
        listing_b = make_listing(
            source=ListingSource.CRAIGSLIST,
            source_id="craigslist-xyz",
            rent_dollars=1800.0,
        )
        assert repo._is_same_unit(listing_a, listing_b) is True

    def test_same_address_rent_within_5pct_is_duplicate(self):
        """
        Landlords sometimes list slightly different prices on different platforms.
        $1,800 on Zillow and $1,795 on Craigslist should be treated as the same unit.
        """
        repo = ListingRepository(session=None)
        listing_a = make_listing(rent_dollars=1800.0)
        listing_b = make_listing(rent_dollars=1795.0)  # 0.28% difference — same unit
        assert repo._is_same_unit(listing_a, listing_b) is True

    def test_same_address_rent_over_5pct_different_not_duplicate(self):
        """
        $1,800 and $1,700 at the same address could be different units in the building.
        Do not deduplicate.
        """
        repo = ListingRepository(session=None)
        listing_a = make_listing(street="100 Oak Ave", rent_dollars=1800.0)
        listing_b = make_listing(street="100 Oak Ave", rent_dollars=1700.0)  # 5.6% diff
        # NOTE: This is a borderline case. The algorithm uses 5% threshold.
        # At 5.6% difference, these are treated as potentially different units.
        assert repo._is_same_unit(listing_a, listing_b) is False

    def test_different_street_same_rent_not_duplicate(self):
        """Two different addresses at the same rent — definitely not duplicates."""
        repo = ListingRepository(session=None)
        listing_a = make_listing(street="123 Main St",  rent_dollars=1800.0)
        listing_b = make_listing(street="456 Oak Ave", rent_dollars=1800.0)
        assert repo._is_same_unit(listing_a, listing_b) is False

    def test_street_abbreviation_variants_are_duplicate(self):
        """
        "123 Main Street" and "123 Main St" should be recognized as the same address.
        The SequenceMatcher ratio should be high enough (>0.8) to catch this.
        """
        repo = ListingRepository(session=None)
        listing_a = make_listing(street="123 Main Street", rent_dollars=1800.0)
        listing_b = make_listing(street="123 Main St",     rent_dollars=1800.0)
        assert repo._is_same_unit(listing_a, listing_b) is True
```

**File: `tests/unit/agents/test_email_tool_verify.py`**

```python
"""
Tests for EmailOutreachTool.verify() — the server-side confirmation step.

The critical behavior: verify() must return False when SendGrid reports failure.
If this breaks, the agent will think emails were delivered when they weren't,
and will never retry via phone or SMS.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from defrosted.agents.tools.email_tool import EmailOutreachTool


@pytest.fixture
def email_tool():
    settings = MagicMock()
    settings.sendgrid_api_key = "test-key"
    settings.outreach_from_email = "agent@defrosted.ai"
    rate_limiter = AsyncMock()
    return EmailOutreachTool(settings=settings, rate_limiter=rate_limiter)


@pytest.mark.asyncio
async def test_verify_returns_true_on_delivered(email_tool):
    """The happy path: SendGrid confirms delivery."""
    mock_response = MagicMock()
    mock_response.to_dict.return_value = {
        "messages": [{"status": "delivered"}]
    }
    email_tool._client.client.messages = MagicMock()
    email_tool._client.client.messages._("test-msg-id").get.return_value = mock_response

    result = await email_tool.verify("test-msg-id")
    assert result is True


@pytest.mark.asyncio
async def test_verify_returns_false_on_bounced(email_tool):
    """If the email bounced, we must not treat it as delivered."""
    mock_response = MagicMock()
    mock_response.to_dict.return_value = {
        "messages": [{"status": "bounced"}]
    }
    email_tool._client.client.messages = MagicMock()
    email_tool._client.client.messages._("test-msg-id").get.return_value = mock_response

    result = await email_tool.verify("test-msg-id")
    assert result is False


@pytest.mark.asyncio
async def test_verify_returns_false_on_timeout(email_tool, monkeypatch):
    """
    If SendGrid never confirms after 5 attempts, return False.
    We don't want the agent stuck forever waiting for a confirmation.
    """
    async def slow_sleep(seconds):
        pass  # don't actually sleep in tests

    monkeypatch.setattr("asyncio.sleep", slow_sleep)

    mock_response = MagicMock()
    mock_response.to_dict.return_value = {"messages": []}   # empty — not yet processed
    email_tool._client.client.messages = MagicMock()
    email_tool._client.client.messages._("test-msg-id").get.return_value = mock_response

    result = await email_tool.verify("test-msg-id")
    assert result is False
```

---

## 11. DATABASE SCHEMA (run this migration first)

```sql
-- Migration: 001_initial_schema.sql
-- Run via: alembic upgrade head

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;    -- pgvector for embeddings

-- ── Users (minimal — Clerk handles auth) ────────────────────────────────────
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_user_id   TEXT UNIQUE NOT NULL,    -- Clerk's external ID
    email           TEXT UNIQUE NOT NULL,
    full_name       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Rental Searches ──────────────────────────────────────────────────────────
CREATE TABLE rental_searches (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES users(id),
    requirements            JSONB NOT NULL,             -- RentalRequirements snapshot
    status                  TEXT NOT NULL DEFAULT 'pending',
    temporal_workflow_id    TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    failure_reason          TEXT
);
CREATE INDEX idx_rental_searches_user_id ON rental_searches(user_id);
CREATE INDEX idx_rental_searches_status  ON rental_searches(status);

-- ── Landlords ────────────────────────────────────────────────────────────────
CREATE TABLE landlords (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                        TEXT,
    email                       TEXT,
    phone                       TEXT,              -- E.164 format
    social_handle               TEXT,
    total_contacts              INT NOT NULL DEFAULT 0,
    total_responses             INT NOT NULL DEFAULT 0,
    total_ghosts                INT NOT NULL DEFAULT 0,
    avg_response_hours          FLOAT,
    preferred_contact_channel   TEXT,
    behavior_embedding          vector(1536),      -- pgvector: landlord behavior fingerprint
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Listings ─────────────────────────────────────────────────────────────────
CREATE TABLE listings (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rental_search_id        UUID NOT NULL REFERENCES rental_searches(id),
    landlord_id             UUID REFERENCES landlords(id),
    source                  TEXT NOT NULL,
    source_listing_id       TEXT NOT NULL,
    source_url              TEXT NOT NULL,
    -- Address fields (denormalized for query performance)
    street                  TEXT NOT NULL,
    unit                    TEXT,
    city                    TEXT NOT NULL,
    state                   CHAR(2) NOT NULL,
    zip_code                TEXT NOT NULL,
    -- PostGIS geography point for geo queries
    location                GEOGRAPHY(POINT, 4326),
    -- Listing attributes
    monthly_rent_cents      INT NOT NULL,
    bedrooms                SMALLINT,
    bathrooms               FLOAT,
    square_feet             INT,
    available_date          DATE,
    lease_duration_months   SMALLINT,
    pets_allowed            BOOLEAN,
    parking_included        BOOLEAN,
    utilities_included      BOOLEAN,
    furnished               BOOLEAN,
    description             TEXT,
    photos                  TEXT[],                -- S3 URLs
    -- State
    status                  TEXT NOT NULL DEFAULT 'active',
    is_duplicate            BOOLEAN NOT NULL DEFAULT FALSE,
    dedup_canonical_id      UUID REFERENCES listings(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (source, source_listing_id)
);
-- Geo index for radius queries
CREATE INDEX idx_listings_location ON listings USING GIST (location);
CREATE INDEX idx_listings_search_id ON listings(rental_search_id);
CREATE INDEX idx_listings_status ON listings(status);

-- ── Outreach Attempts ────────────────────────────────────────────────────────
CREATE TABLE outreach_attempts (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rental_search_id        UUID NOT NULL REFERENCES rental_searches(id),
    listing_id              UUID NOT NULL REFERENCES listings(id),
    landlord_id             UUID NOT NULL REFERENCES landlords(id),
    channel                 TEXT NOT NULL,
    direction               TEXT NOT NULL DEFAULT 'outbound',
    message_body            TEXT NOT NULL,
    subject                 TEXT,
    -- Provider references for verification
    sendgrid_message_id     TEXT,
    twilio_sid              TEXT,
    bland_call_id           TEXT,
    -- Response tracking
    response_body           TEXT,
    responded_at            TIMESTAMPTZ,
    response_sentiment      TEXT,
    attempt_number          SMALLINT NOT NULL DEFAULT 1,
    sent_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_outreach_search_id ON outreach_attempts(rental_search_id);
CREATE INDEX idx_outreach_listing_id ON outreach_attempts(listing_id);

-- ── Event Store (immutable — never UPDATE, only INSERT) ──────────────────────
CREATE TABLE domain_events (
    event_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rental_search_id    UUID NOT NULL REFERENCES rental_searches(id),
    event_type          TEXT NOT NULL,
    sequence            BIGINT NOT NULL,       -- monotonically increasing per search
    payload             JSONB NOT NULL,        -- full event data
    occurred_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (rental_search_id, sequence)        -- no gaps or duplicates in sequence
);
CREATE INDEX idx_events_search_id ON domain_events(rental_search_id);
CREATE INDEX idx_events_type ON domain_events(event_type);

-- ── Leases ───────────────────────────────────────────────────────────────────
CREATE TABLE leases (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rental_search_id            UUID NOT NULL REFERENCES rental_searches(id),
    listing_id                  UUID NOT NULL REFERENCES listings(id),
    landlord_id                 UUID NOT NULL REFERENCES landlords(id),
    user_id                     UUID NOT NULL REFERENCES users(id),
    monthly_rent_cents          INT NOT NULL,
    move_in_date                DATE NOT NULL,
    lease_duration_months       SMALLINT NOT NULL,
    -- Address snapshot (denormalized — listing address at time of signing)
    address_snapshot            JSONB NOT NULL,
    -- Documents
    lease_document_s3_key       TEXT,
    signed_document_s3_key      TEXT,
    docusign_envelope_id        TEXT,
    signed_at                   TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 12. CONFIG AND ENTRYPOINT

**File: `src/defrosted/config.py`**

```python
"""
All configuration in one place. No hardcoded values anywhere else.
Every secret is read from environment variables — never committed to git.

Usage:
    from defrosted.config import get_settings
    settings = get_settings()  # cached singleton
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    environment: str = "development"     # "development" | "staging" | "production"
    log_level: str = "INFO"

    # Database
    database_url: str                    # postgresql+asyncpg://user:pass@host/db
    database_pool_size: int = 20
    database_max_overflow: int = 40

    # Redis
    redis_url: str                       # redis://host:6379/0

    # AWS
    aws_region: str = "us-east-1"
    s3_bucket_name: str
    s3_documents_prefix: str = "documents/"

    # AI
    anthropic_api_key: str
    langsmith_api_key: str | None = None
    langsmith_project: str = "defrosted-production"

    # Communication
    sendgrid_api_key: str
    outreach_from_email: str = "agent@defrosted.ai"
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str            # E.164 format
    bland_ai_api_key: str

    # Browser automation
    browserbase_api_key: str
    browserbase_project_id: str

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "defrosted"
    temporal_task_queue: str = "rental-search-queue"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached singleton Settings instance.
    @lru_cache ensures we only parse environment variables once per process.
    This is safe because settings are read-only after startup.
    """
    return Settings()
```

---

## 13. FINAL INSTRUCTIONS FOR THE CODING AGENT

When implementing this codebase:

```
DO:
✓ Implement every file listed in the project structure
✓ Write the database migration in alembic/versions/
✓ Write a docker-compose.yml with: postgres, redis, temporal, elasticsearch
✓ Write a Makefile with: make dev, make test, make migrate, make lint
✓ Add structlog to every service method — log entry and exit with parameters
✓ Add @pytest.mark.asyncio to every async test
✓ Use pytest fixtures for all database sessions and external service mocks
✓ Write type hints on every function signature, every return type
✓ Run mypy --strict on the entire codebase — zero type errors allowed
✓ Run ruff check — zero linting errors allowed
✓ Every TODO becomes a GitHub issue description in a comment: # TODO(issue-42): ...

DON'T:
✗ Add any import that isn't in the tech stack without asking
✗ Use global state (module-level variables that mutate)
✗ Catch bare Exception: — always catch the specific exception you expect
✗ Write print() — use structlog.get_logger(__name__).info() or .error()
✗ Trust the LLM's self-report of tool success — always call verify()
✗ Skip the disclosure footer in email outreach
✗ Write SQL outside of repository files
✗ Return None when you mean to raise — make failure explicit
✗ Create abstract base classes unless you have 3 concrete implementations
✗ Add a new dependency without adding it to pyproject.toml

PERFORMANCE TARGETS (design for these, don't optimize prematurely):
- API response time: p95 < 200ms for read endpoints, p95 < 500ms for write
- Listing scrape: 50 listings ingested per minute per search
- Outreach throughput: 20 concurrent landlord contacts per search
- Dedup check: < 10ms per listing (uses index, not full table scan)
- Event store write: < 5ms (append-only, no locks)

SECURITY CHECKLIST (verify before shipping):
□ All endpoints require auth except /health and /docs
□ Users can only access their own data (ownership check in every endpoint)
□ All secrets in environment variables, none in code or logs
□ SQL uses parameterized queries (no string formatting)
□ File uploads validate MIME type and size before S3 write
□ Rate limiting on all public endpoints
□ Disclosure header in every outreach message
□ HumanApproval record required before any offer or lease action
□ Event store is append-only (no UPDATE statements on domain_events table)
```

---

*End of prompt. Feed entire document to Opus 4.8.*
