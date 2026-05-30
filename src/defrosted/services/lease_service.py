"""
Lease application service.

Creates the Lease aggregate once a landlord has accepted and the user approved,
and records signing. The actual e-signature exchange (DocuSign) is coordinated
by the lease workflow; this service persists the artifact and the immutable
LeaseSignedEvent that proves what was signed and when.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import structlog

from ..domain.events import LeaseSignedEvent
from ..domain.models import Lease
from ..infrastructure.event_store import EventStore
from ..repositories.lease_repository import LeaseRepository

log = structlog.get_logger(__name__)


class LeaseService:
    def __init__(self, lease_repo: LeaseRepository, event_store: EventStore) -> None:
        self._lease_repo = lease_repo
        self._event_store = event_store

    async def record_signed_lease(
        self,
        *,
        lease: Lease,
        signed_document_s3_key: str,
        docusign_envelope_id: str,
    ) -> Lease:
        """
        Mark a lease signed and append a LeaseSignedEvent. Fails loudly if the
        lease is missing the document references that prove signing happened.
        """
        if not signed_document_s3_key:
            raise ValueError("Cannot record a signed lease without signed_document_s3_key.")

        lease.signed_document_s3_key = signed_document_s3_key
        lease.docusign_envelope_id = docusign_envelope_id
        lease.signed_at = datetime.utcnow()
        await self._lease_repo.save(lease)

        await self._event_store.append(
            LeaseSignedEvent(
                rental_search_id=lease.rental_search_id,
                sequence=0,
                lease_id=lease.id,
                listing_id=lease.listing_id,
                signed_document_s3_key=signed_document_s3_key,
                docusign_envelope_id=docusign_envelope_id,
                monthly_rent_cents=lease.monthly_rent.cents,
                move_in_date=lease.move_in_date,
            )
        )
        log.info("record_signed_lease.done", lease_id=str(lease.id))
        return lease

    async def get_lease(self, lease_id: uuid.UUID) -> Lease | None:
        return await self._lease_repo.get_by_id(lease_id)
