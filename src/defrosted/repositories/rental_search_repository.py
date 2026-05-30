"""
Rental search repository — the aggregate root's persistence.

Requirements are stored as a JSONB snapshot (the migration column
``rental_searches.requirements``). We serialize the RentalRequirements value
object to JSON on write and rehydrate it on read.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text

from ..domain.models import RentalRequirements, RentalSearch, SearchStatus
from .base import BaseRepository

# Statuses that count against a user's concurrent-search limit.
_ACTIVE_STATUSES = (
    SearchStatus.PENDING.value,
    SearchStatus.SEARCHING.value,
    SearchStatus.OUTREACHING.value,
    SearchStatus.AWAITING_APPROVAL.value,
    SearchStatus.APPROVED.value,
    SearchStatus.SIGNING.value,
)


class RentalSearchRepository(BaseRepository[RentalSearch]):
    model_class = RentalSearch

    @staticmethod
    def _row_to_search(row: dict[str, Any]) -> RentalSearch:
        # asyncpg returns jsonb as a str by default; tolerate either form.
        raw_requirements = row["requirements"]
        if isinstance(raw_requirements, str):
            raw_requirements = json.loads(raw_requirements)
        return RentalSearch(
            id=row["id"],
            user_id=row["user_id"],
            requirements=RentalRequirements(**raw_requirements),
            status=SearchStatus(row["status"]),
            temporal_workflow_id=row["temporal_workflow_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
            failure_reason=row["failure_reason"],
        )

    async def get_by_id(self, search_id: uuid.UUID) -> RentalSearch | None:
        result = await self.session.execute(
            text("SELECT * FROM rental_searches WHERE id = :id"),
            {"id": str(search_id)},
        )
        row = result.mappings().first()
        return self._row_to_search(dict(row)) if row else None

    async def count_active_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            text("""
                SELECT COUNT(*) FROM rental_searches
                WHERE user_id = :user_id AND status = ANY(:statuses)
            """),
            {"user_id": str(user_id), "statuses": list(_ACTIVE_STATUSES)},
        )
        return int(result.scalar_one())

    async def save(self, search: RentalSearch) -> RentalSearch:
        await self.session.execute(
            text("""
                INSERT INTO rental_searches (
                    id, user_id, requirements, status, temporal_workflow_id,
                    created_at, updated_at, completed_at, failure_reason
                ) VALUES (
                    :id, :user_id, CAST(:requirements AS JSONB), :status, :temporal_workflow_id,
                    :created_at, :updated_at, :completed_at, :failure_reason
                )
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    temporal_workflow_id = EXCLUDED.temporal_workflow_id,
                    updated_at = EXCLUDED.updated_at,
                    completed_at = EXCLUDED.completed_at,
                    failure_reason = EXCLUDED.failure_reason
            """),
            {
                "id": str(search.id),
                "user_id": str(search.user_id),
                "requirements": json.dumps(search.requirements.model_dump(mode="json")),
                "status": search.status.value,
                "temporal_workflow_id": search.temporal_workflow_id,
                "created_at": search.created_at,
                "updated_at": search.updated_at,
                "completed_at": search.completed_at,
                "failure_reason": search.failure_reason,
            },
        )
        return search
