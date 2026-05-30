"""Response schema for listings surfaced to the user."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from ...domain.models import Listing


class ListingResponse(BaseModel):
    id: uuid.UUID
    source: str
    source_url: str
    full_address: str
    monthly_rent_dollars: float
    bedrooms: int | None
    bathrooms: float | None
    available_date: datetime | None
    status: str
    photos: list[str]

    @classmethod
    def from_domain(cls, listing: Listing) -> ListingResponse:
        return cls(
            id=listing.id,
            source=listing.source.value,
            source_url=listing.source_url,
            full_address=listing.address.full_address,
            monthly_rent_dollars=float(listing.monthly_rent.dollars),
            bedrooms=listing.bedrooms,
            bathrooms=listing.bathrooms,
            available_date=listing.available_date,
            status=listing.status.value,
            photos=list(listing.photos),
        )
