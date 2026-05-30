"""
FastAPI dependencies — the composition root.

This is where concrete collaborators are wired into services: DB sessions,
the LLM requirements parser, and the Temporal workflow gateway. Heavy SDKs
(anthropic, temporalio) are imported lazily inside the methods that use them so
that importing the API does not require the full infra extra to be installed.

Auth: every protected endpoint depends on ``get_current_user``, which verifies
the JWT and returns its claims. No claims → 401.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..domain.models import RentalRequirements
from ..infrastructure.database import get_session
from ..infrastructure.event_store import EventStore
from ..repositories.listing_repository import ListingRepository
from ..repositories.rental_search_repository import RentalSearchRepository
from ..services.rental_search_service import RentalSearchService

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Verify the JWT and return its claims. Raises 401 on any failure."""
    try:
        claims: dict[str, Any] = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc
    if "sub" not in claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )
    return claims


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


class _ClaudeRequirementsParser:
    """Parses free text into RentalRequirements via Claude. Lazily loads the SDK."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def parse(self, raw_requirements: str) -> RentalRequirements:
        import json

        from anthropic import AsyncAnthropic

        from ..agents.prompts import REQUIREMENTS_PARSER_SYSTEM
        from ..domain.value_objects import Money

        client = AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=REQUIREMENTS_PARSER_SYSTEM,
            messages=[{"role": "user", "content": raw_requirements}],
        )
        text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        parsed = json.loads("".join(text_blocks))
        return RentalRequirements(
            city=parsed["city"],
            neighborhoods=parsed.get("neighborhoods", []),
            max_monthly_rent=Money.from_dollars(parsed["max_monthly_rent_dollars"]),
            min_monthly_rent=(
                Money.from_dollars(parsed["min_monthly_rent_dollars"])
                if parsed.get("min_monthly_rent_dollars")
                else None
            ),
            bedrooms=parsed.get("bedrooms"),
            bathrooms=parsed.get("bathrooms"),
            move_in_date=parsed["move_in_date"],
            lease_duration_months=parsed["lease_duration_months"],
            pets_allowed=parsed.get("pets_allowed"),
            parking_required=parsed.get("parking_required", False),
            utilities_included=parsed.get("utilities_included"),
            furnished=parsed.get("furnished"),
            max_commute_minutes=parsed.get("max_commute_minutes"),
            commute_destination=parsed.get("commute_destination"),
            additional_notes=parsed.get("additional_notes"),
        )


class _TemporalWorkflowGateway:
    """Starts and signals the rental-search workflow. Lazily loads the SDK."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def _client(self) -> Any:
        from temporalio.client import Client

        return await Client.connect(
            self._settings.temporal_host, namespace=self._settings.temporal_namespace
        )

    async def start(self, rental_search_id: uuid.UUID) -> str:
        from ..workflows.rental_search_workflow import RentalSearchWorkflow

        client = await self._client()
        workflow_id = f"rental-search-{rental_search_id}"
        await client.start_workflow(
            RentalSearchWorkflow.run,
            str(rental_search_id),
            id=workflow_id,
            task_queue=self._settings.temporal_task_queue,
        )
        return workflow_id

    async def signal_listing_approved(
        self, workflow_id: str, approval_data: dict[str, str]
    ) -> None:
        from ..workflows.rental_search_workflow import RentalSearchWorkflow

        client = await self._client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(RentalSearchWorkflow.user_approved_listing, approval_data)


def get_rental_search_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> RentalSearchService:
    return RentalSearchService(
        search_repo=RentalSearchRepository(session),
        listing_repo=ListingRepository(session),
        event_store=EventStore(session),
        parser=_ClaudeRequirementsParser(settings),
        workflow=_TemporalWorkflowGateway(settings),
    )
