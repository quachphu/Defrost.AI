"""
Agent-run repository.

The persistent record of what the agent *did* during a search is the set of
``outreach_attempts`` — every email/SMS/call it made and every landlord reply.
This file owns that table. (The spec's file structure names this
``agent_run_repository``; the concrete artifact of an agent run is the outreach
log, so that is what lives here. A separate ``agent_runs`` aggregate is not
introduced until there is a concrete need for one — Karpathy rule 5.)
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text

from ..domain.models import OutreachAttempt, OutreachChannel
from .base import BaseRepository


class OutreachAttemptRepository(BaseRepository[OutreachAttempt]):
    model_class = OutreachAttempt

    @staticmethod
    def _row_to_attempt(row: dict[str, Any]) -> OutreachAttempt:
        return OutreachAttempt(
            id=row["id"],
            rental_search_id=row["rental_search_id"],
            listing_id=row["listing_id"],
            landlord_id=row["landlord_id"],
            channel=OutreachChannel(row["channel"]),
            direction=row["direction"],
            message_body=row["message_body"],
            subject=row["subject"],
            sendgrid_message_id=row["sendgrid_message_id"],
            twilio_sid=row["twilio_sid"],
            bland_call_id=row["bland_call_id"],
            response_body=row["response_body"],
            responded_at=row["responded_at"],
            response_sentiment=row["response_sentiment"],
            attempt_number=row["attempt_number"],
            sent_at=row["sent_at"],
        )

    async def get_by_id(self, attempt_id: uuid.UUID) -> OutreachAttempt | None:
        result = await self.session.execute(
            text("SELECT * FROM outreach_attempts WHERE id = :id"),
            {"id": str(attempt_id)},
        )
        row = result.mappings().first()
        return self._row_to_attempt(dict(row)) if row else None

    async def list_for_search(self, rental_search_id: uuid.UUID) -> list[OutreachAttempt]:
        result = await self.session.execute(
            text("""
                SELECT * FROM outreach_attempts
                WHERE rental_search_id = :search_id
                ORDER BY sent_at ASC
            """),
            {"search_id": str(rental_search_id)},
        )
        return [self._row_to_attempt(dict(row)) for row in result.mappings().all()]

    async def save(self, attempt: OutreachAttempt) -> OutreachAttempt:
        await self.session.execute(
            text("""
                INSERT INTO outreach_attempts (
                    id, rental_search_id, listing_id, landlord_id, channel,
                    direction, message_body, subject,
                    sendgrid_message_id, twilio_sid, bland_call_id,
                    response_body, responded_at, response_sentiment,
                    attempt_number, sent_at
                ) VALUES (
                    :id, :rental_search_id, :listing_id, :landlord_id, :channel,
                    :direction, :message_body, :subject,
                    :sendgrid_message_id, :twilio_sid, :bland_call_id,
                    :response_body, :responded_at, :response_sentiment,
                    :attempt_number, :sent_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    response_body = EXCLUDED.response_body,
                    responded_at = EXCLUDED.responded_at,
                    response_sentiment = EXCLUDED.response_sentiment
            """),
            {
                "id": str(attempt.id),
                "rental_search_id": str(attempt.rental_search_id),
                "listing_id": str(attempt.listing_id),
                "landlord_id": str(attempt.landlord_id),
                "channel": attempt.channel.value,
                "direction": attempt.direction,
                "message_body": attempt.message_body,
                "subject": attempt.subject,
                "sendgrid_message_id": attempt.sendgrid_message_id,
                "twilio_sid": attempt.twilio_sid,
                "bland_call_id": attempt.bland_call_id,
                "response_body": attempt.response_body,
                "responded_at": attempt.responded_at,
                "response_sentiment": attempt.response_sentiment,
                "attempt_number": attempt.attempt_number,
                "sent_at": attempt.sent_at,
            },
        )
        return attempt
