"""
Outreach application service.

Sends initial landlord outreach for a set of listings and records each attempt.
The hard rule lives here: an attempt is only recorded as a domain event after
the channel tool's ``verify`` confirms the provider actually sent it
(delegated to agents.verification.verify_and_record_outreach).

Following-up, channel escalation (email → sms → phone) and ghost detection are
driven by the Temporal workflow over time; this service exposes the single
"contact one landlord on one channel" unit those steps compose.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import structlog

from ..agents.tools.base import AgentTool
from ..agents.verification import verify_and_record_outreach
from ..domain.models import Listing, OutreachAttempt, OutreachChannel
from ..infrastructure.event_store import EventStore
from ..repositories.agent_run_repository import OutreachAttemptRepository

log = structlog.get_logger(__name__)


class OutreachService:
    def __init__(
        self,
        email_tool: AgentTool,
        attempt_repo: OutreachAttemptRepository,
        event_store: EventStore,
    ) -> None:
        self._email_tool = email_tool
        self._attempt_repo = attempt_repo
        self._event_store = event_store

    async def contact_landlord_by_email(
        self,
        *,
        rental_search_id: uuid.UUID,
        listing: Listing,
        landlord_email: str,
        renter_name: str,
        authorized_at: datetime,
        subject: str,
        body: str,
        attempt_number: int = 1,
    ) -> OutreachAttempt | None:
        """
        Send one outreach email for a listing, record the attempt, and append a
        verified OutreachSentEvent. Returns the persisted attempt, or None if the
        send could not be verified (caller should escalate to another channel).
        """
        if listing.landlord_id is None:
            raise ValueError(
                f"Listing {listing.id} has no landlord_id; cannot contact a landlord "
                "for a listing whose owner has not been resolved."
            )

        attempt = OutreachAttempt(
            rental_search_id=rental_search_id,
            listing_id=listing.id,
            landlord_id=listing.landlord_id,
            channel=OutreachChannel.EMAIL,
            message_body=body,
            subject=subject,
            attempt_number=attempt_number,
        )

        result = await self._email_tool.execute({
            "rental_search_id": str(rental_search_id),
            "landlord_email": landlord_email,
            "renter_name": renter_name,
            "authorized_at": authorized_at.isoformat(),
            "subject": subject,
            "body": body,
            "attempt_number": attempt_number,
        })

        recorded = await verify_and_record_outreach(
            self._email_tool,
            result,
            event_store=self._event_store,
            rental_search_id=rental_search_id,
            outreach_attempt_id=attempt.id,
            listing_id=listing.id,
            landlord_id=listing.landlord_id,
            channel=OutreachChannel.EMAIL.value,
        )
        if not recorded:
            return None

        attempt.sendgrid_message_id = result.provider_reference
        await self._attempt_repo.save(attempt)
        return attempt
