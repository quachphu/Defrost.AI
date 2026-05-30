"""Response schema for leases."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from ...domain.models import Lease


class LeaseResponse(BaseModel):
    id: uuid.UUID
    full_address: str
    monthly_rent_dollars: float
    move_in_date: datetime
    lease_duration_months: int
    signed_at: datetime | None
    signed_document_s3_key: str | None

    @classmethod
    def from_domain(cls, lease: Lease) -> LeaseResponse:
        return cls(
            id=lease.id,
            full_address=lease.address.full_address,
            monthly_rent_dollars=float(lease.monthly_rent.dollars),
            move_in_date=lease.move_in_date,
            lease_duration_months=lease.lease_duration_months,
            signed_at=lease.signed_at,
            signed_document_s3_key=lease.signed_document_s3_key,
        )
