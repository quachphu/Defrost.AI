"""
REST API for leases — the final artifact of a completed search.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories.lease_repository import LeaseRepository
from ..dependencies import get_current_user, get_db_session
from ..schemas.leases import LeaseResponse

router = APIRouter(prefix="/leases", tags=["leases"])


@router.get(
    "/{lease_id}",
    response_model=LeaseResponse,
    summary="Get a lease the user owns",
)
async def get_lease(
    lease_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> LeaseResponse:
    user_id = uuid.UUID(current_user["sub"])

    lease = await LeaseRepository(session).get_by_id(lease_id)
    if lease is None or lease.user_id != user_id:
        raise HTTPException(status_code=404, detail="Lease not found")

    return LeaseResponse.from_domain(lease)
