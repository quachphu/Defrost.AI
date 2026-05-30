"""
Tests for the listing deduplication algorithm.

We test the BEHAVIOR: given two listings, does the algorithm correctly
identify them as the same unit or different units?

We do NOT test: which internal methods are called, how many SQL queries run,
what the repository's internal state looks like.

Karpathy rule: tests should read like specifications.
"""
import uuid

from defrosted.domain.models import Listing, ListingSource
from defrosted.domain.value_objects import Address, Money
from defrosted.repositories.listing_repository import ListingRepository


def make_listing(
    street: str = "123 Main St",
    city: str = "San Jose",
    state: str = "CA",
    zip_code: str = "95101",
    rent_dollars: float = 1800.0,
    source: ListingSource = ListingSource.ZILLOW,
    source_id: str = "zillow-abc123",
    lat: float = 37.3382,
    lng: float = -121.8863,
) -> Listing:
    """Factory for test listings. Only override what your test cares about."""
    return Listing(
        id=uuid.uuid4(),
        rental_search_id=uuid.uuid4(),
        source=source,
        source_listing_id=source_id,
        source_url=f"https://zillow.com/{source_id}",
        address=Address(street=street, city=city, state=state, zip_code=zip_code),
        monthly_rent=Money.from_dollars(rent_dollars),
        latitude=lat,
        longitude=lng,
    )


class TestListingDeduplication:
    """
    Same physical unit, different platforms → should be flagged as duplicates.
    Different units nearby → should NOT be flagged.
    """

    def test_same_address_same_rent_is_duplicate(self):
        """
        The clearest case: same address, same rent, different platforms.
        This is the most common scenario — a landlord lists on Zillow AND Craigslist.
        """
        repo = ListingRepository(session=None)   # session not needed for unit test

        listing_a = make_listing(
            source=ListingSource.ZILLOW,
            source_id="zillow-abc",
            rent_dollars=1800.0,
        )
        listing_b = make_listing(
            source=ListingSource.CRAIGSLIST,
            source_id="craigslist-xyz",
            rent_dollars=1800.0,
        )
        assert repo._is_same_unit(listing_a, listing_b) is True

    def test_same_address_rent_within_5pct_is_duplicate(self):
        """
        Landlords sometimes list slightly different prices on different platforms.
        $1,800 on Zillow and $1,795 on Craigslist should be treated as the same unit.
        """
        repo = ListingRepository(session=None)
        listing_a = make_listing(rent_dollars=1800.0)
        listing_b = make_listing(rent_dollars=1795.0)  # 0.28% difference — same unit
        assert repo._is_same_unit(listing_a, listing_b) is True

    def test_same_address_rent_over_5pct_different_not_duplicate(self):
        """
        $1,800 and $1,700 at the same address could be different units in the building.
        Do not deduplicate.
        """
        repo = ListingRepository(session=None)
        listing_a = make_listing(street="100 Oak Ave", rent_dollars=1800.0)
        listing_b = make_listing(street="100 Oak Ave", rent_dollars=1700.0)  # 5.6% diff
        # NOTE: This is a borderline case. The algorithm uses 5% threshold.
        # At 5.6% difference, these are treated as potentially different units.
        assert repo._is_same_unit(listing_a, listing_b) is False

    def test_different_street_same_rent_not_duplicate(self):
        """Two different addresses at the same rent — definitely not duplicates."""
        repo = ListingRepository(session=None)
        listing_a = make_listing(street="123 Main St",  rent_dollars=1800.0)
        listing_b = make_listing(street="456 Oak Ave", rent_dollars=1800.0)
        assert repo._is_same_unit(listing_a, listing_b) is False

    def test_street_abbreviation_variants_are_duplicate(self):
        """
        "123 Main Street" and "123 Main St" should be recognized as the same address.
        The SequenceMatcher ratio should be high enough (>0.8) to catch this.
        """
        repo = ListingRepository(session=None)
        listing_a = make_listing(street="123 Main Street", rent_dollars=1800.0)
        listing_b = make_listing(street="123 Main St",     rent_dollars=1800.0)
        assert repo._is_same_unit(listing_a, listing_b) is True
