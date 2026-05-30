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

from .value_objects import Address, Money, PhoneNumber

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
    signed_document_s3_key: str | None = None    # after e-signature
    docusign_envelope_id: str | None = None

    signed_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
