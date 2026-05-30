"""
Rental search application service.

Owns the rules around creating and advancing a rental search:
  - a user may have at most MAX_ACTIVE_SEARCHES_PER_USER active searches
  - status changes go through the domain state machine (can_transition_to)
  - every consequential change appends an immutable event

Provider-specific collaborators (LLM requirements parsing, the Temporal
workflow) are injected so this service stays pure and testable. Their concrete
implementations are wired in the API composition root (api/dependencies.py).

Karpathy rule: the handler-facing methods are short and read top to bottom.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

import structlog

from ..domain.events import SearchStartedEvent, UserApprovedListingEvent
from ..domain.exceptions import (
    InvalidStatusTransitionError,
    SearchNotFoundError,
    TooManyActiveSearchesError,
)
from ..domain.models import RentalRequirements, RentalSearch, SearchStatus
from ..infrastructure.event_store import EventStore
from ..repositories.listing_repository import ListingRepository
from ..repositories.rental_search_repository import RentalSearchRepository

log = structlog.get_logger(__name__)

MAX_ACTIVE_SEARCHES_PER_USER = 3


class RequirementsParser(Protocol):
    """Turns the renter's free text into structured requirements (LLM-backed)."""

    async def parse(self, raw_requirements: str) -> RentalRequirements: ...


class WorkflowGateway(Protocol):
    """Starts and signals the Temporal rental-search workflow."""

    async def start(self, rental_search_id: uuid.UUID) -> str: ...

    async def signal_listing_approved(
        self, workflow_id: str, approval_data: dict[str, str]
    ) -> None: ...


class RentalSearchService:
    def __init__(
        self,
        search_repo: RentalSearchRepository,
        listing_repo: ListingRepository,
        event_store: EventStore,
        parser: RequirementsParser,
        workflow: WorkflowGateway,
    ) -> None:
        self._search_repo = search_repo
        self._listing_repo = listing_repo
        self._event_store = event_store
        self._parser = parser
        self._workflow = workflow

    async def create_search(
        self, user_id: uuid.UUID, raw_requirements: str
    ) -> RentalSearch:
        log.info("create_search.start", user_id=str(user_id))

        active = await self._search_repo.count_active_for_user(user_id)
        if active >= MAX_ACTIVE_SEARCHES_PER_USER:
            raise TooManyActiveSearchesError(user_id, MAX_ACTIVE_SEARCHES_PER_USER)

        requirements = await self._parser.parse(raw_requirements)
        search = RentalSearch(user_id=user_id, requirements=requirements)
        await self._search_repo.save(search)

        workflow_id = await self._workflow.start(search.id)
        search.temporal_workflow_id = workflow_id
        search.updated_at = datetime.utcnow()
        await self._search_repo.save(search)

        await self._event_store.append(
            SearchStartedEvent(
                rental_search_id=search.id,
                sequence=0,
                user_id=user_id,
                requirements_snapshot=requirements.model_dump(mode="json"),
            )
        )
        log.info("create_search.done", search_id=str(search.id), workflow_id=workflow_id)
        return search

    async def get_search(self, search_id: uuid.UUID) -> RentalSearch | None:
        return await self._search_repo.get_by_id(search_id)

    async def approve_listing(
        self, search_id: uuid.UUID, listing_id: uuid.UUID, user_id: uuid.UUID
    ) -> RentalSearch:
        log.info("approve_listing.start", search_id=str(search_id), listing_id=str(listing_id))

        search = await self._search_repo.get_by_id(search_id)
        if search is None:
            raise SearchNotFoundError(search_id)

        if not search.can_transition_to(SearchStatus.APPROVED):
            raise InvalidStatusTransitionError(search.status.value, SearchStatus.APPROVED.value)

        listing = await self._listing_repo.get_by_id(listing_id)
        if listing is None:
            raise SearchNotFoundError(search_id)  # listing belongs to the search; treat as 404

        search.status = SearchStatus.APPROVED
        search.updated_at = datetime.utcnow()
        await self._search_repo.save(search)

        if search.temporal_workflow_id is not None:
            await self._workflow.signal_listing_approved(
                search.temporal_workflow_id, {"listing_id": str(listing_id)}
            )

        await self._event_store.append(
            UserApprovedListingEvent(
                rental_search_id=search.id,
                sequence=0,
                approval_id=uuid.uuid4(),
                listing_id=listing_id,
                approved_monthly_rent_cents=listing.monthly_rent.cents,
            )
        )
        log.info("approve_listing.done", search_id=str(search.id))
        return search
