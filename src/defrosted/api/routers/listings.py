"""
REST API for listings surfaced during a search.

Ownership is enforced transitively: a listing is visible only to the user who
owns the rental search it belongs to.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories.listing_repository import ListingRepository
from ...repositories.rental_search_repository import RentalSearchRepository
from ..dependencies import get_current_user, get_db_session
from ..schemas.listings import ListingResponse

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get(
    "/{listing_id}",
    response_model=ListingResponse,
    summary="Get a single listing the user owns",
)
async def get_listing(
    listing_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ListingResponse:
    user_id = uuid.UUID(current_user["sub"])

    listing = await ListingRepository(session).get_by_id(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    search = await RentalSearchRepository(session).get_by_id(listing.rental_search_id)
    if search is None or search.user_id != user_id:
        raise HTTPException(status_code=404, detail="Listing not found")

    return ListingResponse.from_domain(listing)
