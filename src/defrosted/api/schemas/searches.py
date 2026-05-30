"""
Request/response schemas for the searches API.

These are NOT domain models. The domain RentalSearch carries Money value
objects and internal fields; the wire format exposes plain JSON the client
needs. Conversion happens in ``from_domain``.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from ...domain.models import RentalSearch


class CreateSearchRequest(BaseModel):
    requirements_text: str = Field(
        ...,
        min_length=1,
        description="The renter's free-text description of what they need.",
    )


class RequirementsView(BaseModel):
    city: str
    neighborhoods: list[str]
    max_monthly_rent_dollars: float
    min_monthly_rent_dollars: float | None
    bedrooms: int | None
    bathrooms: float | None
    move_in_date: datetime
    lease_duration_months: int


class SearchResponse(BaseModel):
    id: uuid.UUID
    status: str
    requirements: RequirementsView
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    failure_reason: str | None

    @classmethod
    def from_domain(cls, search: RentalSearch) -> SearchResponse:
        req = search.requirements
        return cls(
            id=search.id,
            status=search.status.value,
            requirements=RequirementsView(
                city=req.city,
                neighborhoods=list(req.neighborhoods),
                max_monthly_rent_dollars=float(req.max_monthly_rent.dollars),
                min_monthly_rent_dollars=(
                    float(req.min_monthly_rent.dollars) if req.min_monthly_rent else None
                ),
                bedrooms=req.bedrooms,
                bathrooms=req.bathrooms,
                move_in_date=req.move_in_date,
                lease_duration_months=req.lease_duration_months,
            ),
            created_at=search.created_at,
            updated_at=search.updated_at,
            completed_at=search.completed_at,
            failure_reason=search.failure_reason,
        )


class SearchListResponse(BaseModel):
    searches: list[SearchResponse]
    total: int
