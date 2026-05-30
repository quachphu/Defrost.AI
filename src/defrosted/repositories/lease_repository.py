"""
Lease repository.

The address is stored as a JSONB snapshot (``leases.address_snapshot``) so the
lease records the address exactly as it was at signing time, independent of any
later edits to the listing.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text

from ..domain.models import Lease
from ..domain.value_objects import Address, Money
from .base import BaseRepository


class LeaseRepository(BaseRepository[Lease]):
    model_class = Lease

    @staticmethod
    def _row_to_lease(row: dict[str, Any]) -> Lease:
        raw_address = row["address_snapshot"]
        if isinstance(raw_address, str):
            raw_address = json.loads(raw_address)
        return Lease(
            id=row["id"],
            rental_search_id=row["rental_search_id"],
            listing_id=row["listing_id"],
            landlord_id=row["landlord_id"],
            user_id=row["user_id"],
            monthly_rent=Money(cents=row["monthly_rent_cents"]),
            move_in_date=row["move_in_date"],
            lease_duration_months=row["lease_duration_months"],
            address=Address(**raw_address),
            lease_document_s3_key=row["lease_document_s3_key"],
            signed_document_s3_key=row["signed_document_s3_key"],
            docusign_envelope_id=row["docusign_envelope_id"],
            signed_at=row["signed_at"],
            created_at=row["created_at"],
        )

    async def get_by_id(self, lease_id: uuid.UUID) -> Lease | None:
        result = await self.session.execute(
            text("SELECT * FROM leases WHERE id = :id"),
            {"id": str(lease_id)},
        )
        row = result.mappings().first()
        return self._row_to_lease(dict(row)) if row else None

    async def save(self, lease: Lease) -> Lease:
        await self.session.execute(
            text("""
                INSERT INTO leases (
                    id, rental_search_id, listing_id, landlord_id, user_id,
                    monthly_rent_cents, move_in_date, lease_duration_months,
                    address_snapshot, lease_document_s3_key, signed_document_s3_key,
                    docusign_envelope_id, signed_at, created_at
                ) VALUES (
                    :id, :rental_search_id, :listing_id, :landlord_id, :user_id,
                    :monthly_rent_cents, :move_in_date, :lease_duration_months,
                    CAST(:address_snapshot AS JSONB), :lease_document_s3_key,
                    :signed_document_s3_key, :docusign_envelope_id, :signed_at, :created_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    signed_document_s3_key = EXCLUDED.signed_document_s3_key,
                    docusign_envelope_id = EXCLUDED.docusign_envelope_id,
                    signed_at = EXCLUDED.signed_at
            """),
            {
                "id": str(lease.id),
                "rental_search_id": str(lease.rental_search_id),
                "listing_id": str(lease.listing_id),
                "landlord_id": str(lease.landlord_id),
                "user_id": str(lease.user_id),
                "monthly_rent_cents": lease.monthly_rent.cents,
                "move_in_date": lease.move_in_date,
                "lease_duration_months": lease.lease_duration_months,
                "address_snapshot": json.dumps(lease.address.model_dump(mode="json")),
                "lease_document_s3_key": lease.lease_document_s3_key,
                "signed_document_s3_key": lease.signed_document_s3_key,
                "docusign_envelope_id": lease.docusign_envelope_id,
                "signed_at": lease.signed_at,
                "created_at": lease.created_at,
            },
        )
        return lease
