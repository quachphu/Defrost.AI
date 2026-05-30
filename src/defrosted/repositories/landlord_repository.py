"""
Landlord repository.

The landlord profile accumulates behavioral metrics (response rate, ghost count,
preferred channel) across searches — this is the data moat described in the spec.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text

from ..domain.models import Landlord, OutreachChannel
from ..domain.value_objects import PhoneNumber
from .base import BaseRepository


class LandlordRepository(BaseRepository[Landlord]):
    model_class = Landlord

    @staticmethod
    def _row_to_landlord(row: dict[str, Any]) -> Landlord:
        return Landlord(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            phone=PhoneNumber(e164=row["phone"]) if row["phone"] else None,
            social_handle=row["social_handle"],
            total_contacts=row["total_contacts"],
            total_responses=row["total_responses"],
            total_ghosts=row["total_ghosts"],
            avg_response_hours=row["avg_response_hours"],
            preferred_contact_channel=(
                OutreachChannel(row["preferred_contact_channel"])
                if row["preferred_contact_channel"]
                else None
            ),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_by_id(self, landlord_id: uuid.UUID) -> Landlord | None:
        result = await self.session.execute(
            text("SELECT * FROM landlords WHERE id = :id"),
            {"id": str(landlord_id)},
        )
        row = result.mappings().first()
        return self._row_to_landlord(dict(row)) if row else None

    async def find_by_email(self, email: str) -> Landlord | None:
        result = await self.session.execute(
            text("SELECT * FROM landlords WHERE email = :email LIMIT 1"),
            {"email": email},
        )
        row = result.mappings().first()
        return self._row_to_landlord(dict(row)) if row else None

    async def save(self, landlord: Landlord) -> Landlord:
        await self.session.execute(
            text("""
                INSERT INTO landlords (
                    id, name, email, phone, social_handle,
                    total_contacts, total_responses, total_ghosts,
                    avg_response_hours, preferred_contact_channel,
                    created_at, updated_at
                ) VALUES (
                    :id, :name, :email, :phone, :social_handle,
                    :total_contacts, :total_responses, :total_ghosts,
                    :avg_response_hours, :preferred_contact_channel,
                    :created_at, :updated_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    email = EXCLUDED.email,
                    phone = EXCLUDED.phone,
                    social_handle = EXCLUDED.social_handle,
                    total_contacts = EXCLUDED.total_contacts,
                    total_responses = EXCLUDED.total_responses,
                    total_ghosts = EXCLUDED.total_ghosts,
                    avg_response_hours = EXCLUDED.avg_response_hours,
                    preferred_contact_channel = EXCLUDED.preferred_contact_channel,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "id": str(landlord.id),
                "name": landlord.name,
                "email": landlord.email,
                "phone": landlord.phone.e164 if landlord.phone else None,
                "social_handle": landlord.social_handle,
                "total_contacts": landlord.total_contacts,
                "total_responses": landlord.total_responses,
                "total_ghosts": landlord.total_ghosts,
                "avg_response_hours": landlord.avg_response_hours,
                "preferred_contact_channel": (
                    landlord.preferred_contact_channel.value
                    if landlord.preferred_contact_channel
                    else None
                ),
                "created_at": landlord.created_at,
                "updated_at": landlord.updated_at,
            },
        )
        return landlord
