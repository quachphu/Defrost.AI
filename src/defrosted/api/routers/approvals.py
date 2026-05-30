"""
REST API for the human-approval gate.

The approve action itself lives on the searches router
(POST /searches/{id}/approve) because it mutates the search. This router
exposes the read side: whether a search is currently waiting on the user and,
when it is, surfaces that state to the dashboard.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...domain.models import SearchStatus
from ...services.rental_search_service import RentalSearchService
from ..dependencies import get_current_user, get_rental_search_service

router = APIRouter(prefix="/searches", tags=["approvals"])


class ApprovalStateResponse(BaseModel):
    search_id: uuid.UUID
    awaiting_approval: bool
    status: str


@router.get(
    "/{search_id}/approval",
    response_model=ApprovalStateResponse,
    summary="Check whether a search is waiting for the user to choose a listing",
)
async def get_approval_state(
    search_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    service: RentalSearchService = Depends(get_rental_search_service),
) -> ApprovalStateResponse:
    user_id = uuid.UUID(current_user["sub"])

    search = await service.get_search(search_id=search_id)
    if search is None or search.user_id != user_id:
        raise HTTPException(status_code=404, detail="Search not found")

    return ApprovalStateResponse(
        search_id=search.id,
        awaiting_approval=search.status == SearchStatus.AWAITING_APPROVAL,
        status=search.status.value,
    )
