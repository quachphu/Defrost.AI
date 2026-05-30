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
