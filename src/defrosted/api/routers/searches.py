"""
REST API for rental searches.

Security applied at this layer:
1. Every endpoint requires a valid JWT (via Depends(get_current_user))
2. Users can only access their own searches (ownership check on every endpoint)
3. Rate limiting on search creation: max 3 active searches per user
4. Input validation: Pydantic schemas for every request body
5. No internal IDs in error messages (don't tell the user what table we use)

Karpathy rule: the route handler is thin. Business logic lives in the service layer.
The handler: validate input → call service → return response. That's it.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from ...domain.exceptions import TooManyActiveSearchesError
from ...domain.models import SearchStatus
from ...services.rental_search_service import RentalSearchService
from ..dependencies import get_current_user, get_rental_search_service
from ..schemas.searches import CreateSearchRequest, SearchResponse

router = APIRouter(prefix="/searches", tags=["rental-searches"])


@router.post(
    "/",
    response_model=SearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new rental search",
    description=(
        "Parses the renter's natural language requirements, creates a search record, "
        "and starts the Temporal workflow. Returns immediately — the search runs async."
    ),
)
async def create_search(
    body: CreateSearchRequest,
    current_user: dict = Depends(get_current_user),
    service: RentalSearchService = Depends(get_rental_search_service),
) -> SearchResponse:
    user_id = uuid.UUID(current_user["sub"])

    # Service enforces: max 3 active searches per user
    try:
        search = await service.create_search(
            user_id=user_id,
            raw_requirements=body.requirements_text,
        )
    except TooManyActiveSearchesError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return SearchResponse.from_domain(search)


@router.get(
    "/{search_id}",
    response_model=SearchResponse,
    summary="Get search status and results",
)
async def get_search(
    search_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    service: RentalSearchService = Depends(get_rental_search_service),
) -> SearchResponse:
    user_id = uuid.UUID(current_user["sub"])

    search = await service.get_search(search_id=search_id)
    if search is None:
        # Use 404 for both "not found" and "not yours" — don't leak existence
        raise HTTPException(status_code=404, detail="Search not found")

    if search.user_id != user_id:
        raise HTTPException(status_code=404, detail="Search not found")

    return SearchResponse.from_domain(search)


@router.post(
    "/{search_id}/approve",
    response_model=SearchResponse,
    summary="Approve a listing — unblocks the agent workflow",
    description=(
        "The user selects their preferred listing. This sends a Temporal signal "
        "to the waiting workflow, which then proceeds to submit the offer."
    ),
)
async def approve_listing(
    search_id: uuid.UUID,
    listing_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    service: RentalSearchService = Depends(get_rental_search_service),
) -> SearchResponse:
    user_id = uuid.UUID(current_user["sub"])

    search = await service.get_search(search_id=search_id)
    if search is None or search.user_id != user_id:
        raise HTTPException(status_code=404, detail="Search not found")

    if search.status != SearchStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Search is not awaiting approval. Current status: {search.status.value}",
        )

    updated_search = await service.approve_listing(
        search_id=search_id,
        listing_id=listing_id,
        user_id=user_id,
    )
    return SearchResponse.from_domain(updated_search)
