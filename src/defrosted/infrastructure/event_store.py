"""
Event sourcing log writer.

The event store is APPEND-ONLY. We never UPDATE or DELETE rows in
``domain_events`` (security checklist §13). Each event gets the next sequence
number for its rental_search_id; the UNIQUE (rental_search_id, sequence)
constraint guarantees no gaps or duplicates.

Karpathy rule: this file holds the only INSERT into domain_events. If you need
to write an event, you call append() — there is no other path.
"""
from __future__ import annotations

import json
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.events import DomainEvent


class EventStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(self, event: DomainEvent) -> int:
        """
        Append an event for its rental_search_id and return its sequence number.

        We compute the next sequence inside the same transaction as the insert.
        Concurrent appends to the same search are serialized by the UNIQUE
        constraint: a loser gets an IntegrityError and the caller retries.
        """
        next_sequence = await self._next_sequence(event.rental_search_id)
        payload = json.dumps(event.model_dump(mode="json"))
        await self.session.execute(
            text("""
                INSERT INTO domain_events
                    (event_id, rental_search_id, event_type, sequence, payload, occurred_at)
                VALUES
                    (:event_id, :rental_search_id, :event_type, :sequence,
                     CAST(:payload AS JSONB), :occurred_at)
            """),
            {
                "event_id": str(event.event_id),
                "rental_search_id": str(event.rental_search_id),
                "event_type": event.event_type,
                "sequence": next_sequence,
                "payload": payload,
                "occurred_at": event.occurred_at,
            },
        )
        return next_sequence

    async def _next_sequence(self, rental_search_id: uuid.UUID) -> int:
        result = await self.session.execute(
            text("""
                SELECT COALESCE(MAX(sequence), 0) + 1 AS next_seq
                FROM domain_events
                WHERE rental_search_id = :search_id
            """),
            {"search_id": str(rental_search_id)},
        )
        return int(result.scalar_one())
