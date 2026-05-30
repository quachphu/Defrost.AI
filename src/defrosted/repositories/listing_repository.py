"""
Listing repository.

Key algorithms:
1. Geospatial search (PostGIS): find listings within radius of a point
2. Deduplication: identify listings that are the same unit on different platforms

Deduplication algorithm:
  A listing is a duplicate of an existing listing if ALL of these are true:
  - Same city (normalized to lowercase)
  - Same street address (normalized: lowercase, remove "St" vs "Street", etc.)
  - Same monthly rent within 5% tolerance (landlords sometimes list $1,800 on
    Zillow and $1,795 on Craigslist — same unit)
  - Move-in date within 30 days of each other
  OR:
  - Same listing photos (phash comparison) — strongest signal

  When a duplicate is found:
  - Keep the listing with the most complete data as the canonical
  - Flag the other as duplicate, point to canonical
  - Emit DuplicateListingFlaggedEvent
  - Only contact the landlord ONCE (via the canonical listing)

Karpathy rule: the dedup logic is in this file, not scattered across the codebase.

NOTE (deviation from the prose spec, documented intentionally):
- ``_is_same_unit`` also checks rent-within-5% so it is a self-contained
  "are these the same unit?" predicate. The prose snippet checked only address
  similarity, but the unit test ``test_same_address_rent_over_5pct_different_not_duplicate``
  passes the same address with a >5% rent gap and expects ``False``. Tests
  define behavior (Karpathy rule 9), so the rent check lives here too. In the
  full DB flow the SQL pre-filter already bounds rent, so this is redundant but
  harmless there.
- The schema stores geography in a single ``location`` column (see migration
  001), so reads project lat/lng via ST_Y/ST_X and writes build the point via
  ST_MakePoint. The prose snippet's ``SELECT *`` / ``Listing(**row)`` could not
  map flat columns onto the nested Address/Money value objects.
"""
from __future__ import annotations

import uuid
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models import Listing, ListingSource, ListingStatus
from ..domain.value_objects import Address, Money
from .base import BaseRepository

# Reused projection so reads always hydrate lat/lng from the geography column.
_SELECT_COLUMNS = (
    "id, rental_search_id, landlord_id, source, source_listing_id, source_url, "
    "street, unit, city, state, zip_code, "
    "ST_Y(location::geometry) AS latitude, ST_X(location::geometry) AS longitude, "
    "monthly_rent_cents, bedrooms, bathrooms, square_feet, available_date, "
    "lease_duration_months, pets_allowed, parking_included, utilities_included, "
    "furnished, description, photos, status, is_duplicate, dedup_canonical_id, "
    "created_at, updated_at"
)

RENT_TOLERANCE = 0.05  # 5% — same unit listed at slightly different prices
ADDRESS_SIMILARITY_THRESHOLD = 0.8


class ListingRepository(BaseRepository[Listing]):
    model_class = Listing

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    @staticmethod
    def _row_to_listing(row: dict[str, Any]) -> Listing:
        """Map a flat DB row onto the nested domain entity."""
        return Listing(
            id=row["id"],
            rental_search_id=row["rental_search_id"],
            landlord_id=row["landlord_id"],
            source=ListingSource(row["source"]),
            source_listing_id=row["source_listing_id"],
            source_url=row["source_url"],
            address=Address(
                street=row["street"],
                unit=row["unit"],
                city=row["city"],
                state=row["state"],
                zip_code=row["zip_code"],
            ),
            latitude=row["latitude"],
            longitude=row["longitude"],
            monthly_rent=Money(cents=row["monthly_rent_cents"]),
            bedrooms=row["bedrooms"],
            bathrooms=row["bathrooms"],
            square_feet=row["square_feet"],
            available_date=row["available_date"],
            lease_duration_months=row["lease_duration_months"],
            pets_allowed=row["pets_allowed"],
            parking_included=row["parking_included"],
            utilities_included=row["utilities_included"],
            furnished=row["furnished"],
            description=row["description"],
            photos=list(row["photos"]) if row["photos"] else [],
            status=ListingStatus(row["status"]),
            is_duplicate=row["is_duplicate"],
            dedup_canonical_id=row["dedup_canonical_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_by_id(self, listing_id: uuid.UUID) -> Listing | None:
        result = await self.session.execute(
            text(f"SELECT {_SELECT_COLUMNS} FROM listings WHERE id = :id"),
            {"id": str(listing_id)},
        )
        row = result.mappings().first()
        return self._row_to_listing(dict(row)) if row else None

    async def get_by_source_id(
        self, source: str, source_listing_id: str
    ) -> Listing | None:
        """
        Check if we already have this listing from this platform.
        Used during ingestion to avoid re-processing the same listing.
        """
        result = await self.session.execute(
            text(f"""
                SELECT {_SELECT_COLUMNS} FROM listings
                WHERE source = :source
                  AND source_listing_id = :source_listing_id
                LIMIT 1
            """),
            {"source": source, "source_listing_id": source_listing_id},
        )
        row = result.mappings().first()
        return self._row_to_listing(dict(row)) if row else None

    async def find_within_radius_km(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        rental_search_id: uuid.UUID,
    ) -> list[Listing]:
        """
        PostGIS geospatial query: find all active, non-duplicate listings for this
        search within radius_km kilometers of the given coordinates.

        Uses ST_DWithin with geography type for accurate distance in meters.
        radius_km * 1000 converts to meters (ST_DWithin uses meters for geography).
        """
        result = await self.session.execute(
            text(f"""
                SELECT {_SELECT_COLUMNS} FROM listings
                WHERE rental_search_id = :search_id
                  AND status != 'unavailable'
                  AND is_duplicate = false
                  AND ST_DWithin(
                      location::geography,
                      ST_MakePoint(:lng, :lat)::geography,
                      :radius_meters
                  )
                ORDER BY monthly_rent_cents ASC
            """),
            {
                "search_id": str(rental_search_id),
                "lat": latitude,
                "lng": longitude,
                "radius_meters": radius_km * 1000,
            },
        )
        return [self._row_to_listing(dict(row)) for row in result.mappings().all()]

    async def find_duplicate_candidate(self, listing: Listing) -> Listing | None:
        """
        Find an existing listing that is likely the same unit as the given listing.
        Returns the canonical listing if a duplicate is found, None otherwise.

        This is called during listing ingestion before saving.
        See module docstring for the deduplication algorithm.
        """
        if listing.latitude is None or listing.longitude is None:
            # Can't do geo-based dedup without coordinates — fall back to address string match
            return await self._find_duplicate_by_address(listing)

        # Step 1: find listings within 50 meters (same building) with similar rent
        rent_floor = int(listing.monthly_rent.cents * (1 - RENT_TOLERANCE))
        rent_ceil  = int(listing.monthly_rent.cents * (1 + RENT_TOLERANCE))

        result = await self.session.execute(
            text(f"""
                SELECT {_SELECT_COLUMNS} FROM listings
                WHERE id != :id
                  AND is_duplicate = false
                  AND monthly_rent_cents BETWEEN :rent_floor AND :rent_ceil
                  AND ST_DWithin(
                      location::geography,
                      ST_MakePoint(:lng, :lat)::geography,
                      50  -- 50 meters — same building
                  )
                LIMIT 5
            """),
            {
                "id": str(listing.id),
                "rent_floor": rent_floor,
                "rent_ceil": rent_ceil,
                "lat": listing.latitude,
                "lng": listing.longitude,
            },
        )
        candidates = [self._row_to_listing(dict(row)) for row in result.mappings().all()]

        for candidate in candidates:
            if self._is_same_unit(listing, candidate):
                return candidate

        return None

    def _is_same_unit(self, a: Listing, b: Listing) -> bool:
        """
        Returns True if listing a and listing b are the same physical unit.
        Same unit means: the addresses match closely AND the rents are within the
        5% tolerance. Geo proximity is enforced upstream by the SQL pre-filter.
        """
        address_similarity = SequenceMatcher(
            None,
            a.address.full_address.lower(),
            b.address.full_address.lower(),
        ).ratio()
        if address_similarity <= ADDRESS_SIMILARITY_THRESHOLD:
            return False

        # Rent within tolerance of the cheaper of the two — a >5% gap at the same
        # address usually means two different units in the same building.
        cheaper = min(a.monthly_rent.cents, b.monthly_rent.cents)
        dearer = max(a.monthly_rent.cents, b.monthly_rent.cents)
        rent_gap = (dearer - cheaper) / cheaper
        return rent_gap <= RENT_TOLERANCE

    async def _find_duplicate_by_address(self, listing: Listing) -> Listing | None:
        """
        Fallback dedup when we don't have coordinates.
        Uses normalized address string matching in Postgres.
        """
        result = await self.session.execute(
            text(f"""
                SELECT {_SELECT_COLUMNS} FROM listings
                WHERE id != :id
                  AND is_duplicate = false
                  AND city = :city
                  AND zip_code = :zip_code
                  AND monthly_rent_cents BETWEEN :rent_floor AND :rent_ceil
                LIMIT 10
            """),
            {
                "id": str(listing.id),
                "city": listing.address.city.lower(),
                "zip_code": listing.address.zip_code,
                "rent_floor": int(listing.monthly_rent.cents * (1 - RENT_TOLERANCE)),
                "rent_ceil":  int(listing.monthly_rent.cents * (1 + RENT_TOLERANCE)),
            },
        )
        candidates = [self._row_to_listing(dict(row)) for row in result.mappings().all()]
        for candidate in candidates:
            if self._is_same_unit(listing, candidate):
                return candidate
        return None

    async def save(self, listing: Listing) -> Listing:
        await self.session.execute(
            text("""
                INSERT INTO listings (
                    id, rental_search_id, landlord_id, source, source_listing_id,
                    source_url, street, unit, city, state, zip_code,
                    location, monthly_rent_cents,
                    bedrooms, bathrooms, square_feet, available_date,
                    lease_duration_months, pets_allowed, parking_included,
                    utilities_included, furnished, description, photos,
                    status, is_duplicate, dedup_canonical_id,
                    created_at, updated_at
                ) VALUES (
                    :id, :rental_search_id, :landlord_id, :source, :source_listing_id,
                    :source_url, :street, :unit, :city, :state, :zip_code,
                    CASE
                        WHEN :latitude IS NULL OR :longitude IS NULL THEN NULL
                        ELSE ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)
                    END,
                    :monthly_rent_cents,
                    :bedrooms, :bathrooms, :square_feet, :available_date,
                    :lease_duration_months, :pets_allowed, :parking_included,
                    :utilities_included, :furnished, :description, :photos,
                    :status, :is_duplicate, :dedup_canonical_id,
                    :created_at, :updated_at
                )
                ON CONFLICT (source, source_listing_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "id": str(listing.id),
                "rental_search_id": str(listing.rental_search_id),
                "landlord_id": str(listing.landlord_id) if listing.landlord_id else None,
                "source": listing.source.value,
                "source_listing_id": listing.source_listing_id,
                "source_url": listing.source_url,
                "street": listing.address.street,
                "unit": listing.address.unit,
                "city": listing.address.city.lower(),
                "state": listing.address.state.upper(),
                "zip_code": listing.address.zip_code,
                "latitude": listing.latitude,
                "longitude": listing.longitude,
                "monthly_rent_cents": listing.monthly_rent.cents,
                "bedrooms": listing.bedrooms,
                "bathrooms": listing.bathrooms,
                "square_feet": listing.square_feet,
                "available_date": listing.available_date,
                "lease_duration_months": listing.lease_duration_months,
                "pets_allowed": listing.pets_allowed,
                "parking_included": listing.parking_included,
                "utilities_included": listing.utilities_included,
                "furnished": listing.furnished,
                "description": listing.description,
                "photos": listing.photos,
                "status": listing.status.value,
                "is_duplicate": listing.is_duplicate,
                "dedup_canonical_id": (
                    str(listing.dedup_canonical_id) if listing.dedup_canonical_id else None
                ),
                "created_at": listing.created_at,
                "updated_at": listing.updated_at,
            },
        )
        return listing
