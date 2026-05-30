"""
Temporal activities for the rental-search workflow.

Activities are the side-effecting workers the workflow coordinates. Each does
ONE thing and returns a JSON-serializable result (Temporal serializes activity
inputs/outputs). They open their own DB session via ``session_scope`` because
activities run in the worker process, not inside a request.

Where a step depends on a capability that is not yet built (per-site scraping
adapters, DocuSign envelope exchange), the activity raises NotImplementedError
with a precise message rather than silently returning empty data — a silent
empty result would look to the user like "no apartments exist".
"""
from __future__ import annotations

import uuid
from typing import Any

import structlog
from temporalio import activity

log = structlog.get_logger(__name__)


@activity.defn
async def scrape_listings_activity(rental_search_id: str) -> list[dict[str, Any]]:
    """Scrape listings across supported platforms for this search."""
    log.info("scrape_listings_activity.start", rental_search_id=rental_search_id)
    raise NotImplementedError(
        "Listing scraping requires per-site adapters (see agents/tools/browser_tool.py). "
        "Register and test a site adapter before running this activity end to end."
    )


@activity.defn
async def deduplicate_listings_activity(
    rental_search_id: str, listings: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Flag cross-platform duplicates, keeping the most complete as canonical."""
    log.info(
        "deduplicate_listings_activity.start",
        rental_search_id=rental_search_id,
        count=len(listings),
    )
    # Dedup logic lives in ListingRepository.find_duplicate_candidate; this
    # activity wires it once listings are persisted by the scrape step.
    raise NotImplementedError(
        "Deduplication runs against persisted listings produced by "
        "scrape_listings_activity, which is not yet implemented."
    )


@activity.defn
async def contact_landlords_activity(
    rental_search_id: str, unique_listings: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Send initial outreach to up to 20 unique listings; return attempt refs."""
    log.info(
        "contact_landlords_activity.start",
        rental_search_id=rental_search_id,
        count=len(unique_listings),
    )
    raise NotImplementedError(
        "Outreach requires resolved landlord contact details from the (not yet "
        "implemented) scrape/enrich step. OutreachService.contact_landlord_by_email "
        "is the unit this will compose."
    )


@activity.defn
async def wait_for_responses_activity(
    rental_search_id: str, outreach_results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Poll for landlord responses over 48–72h, sending follow-ups; return confirmed."""
    log.info("wait_for_responses_activity.start", rental_search_id=rental_search_id)
    raise NotImplementedError(
        "Response polling depends on inbound parsing (Nylas) which is not yet wired."
    )


@activity.defn
async def build_approval_options_activity(
    rental_search_id: str, confirmed_listings: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Build the top 3–5 options to present to the user for approval."""
    log.info("build_approval_options_activity.start", rental_search_id=rental_search_id)
    # Once confirmed listings are persisted, this ranks and trims them. The
    # ranking heuristic is deferred until there is real confirmed-listing data.
    raise NotImplementedError(
        "Approval-option ranking runs on confirmed listings from the response step."
    )


@activity.defn
async def submit_offer_activity(
    rental_search_id: str, selected_listing_id: str, approval: dict[str, Any]
) -> dict[str, Any]:
    """Submit the user-approved offer to the landlord."""
    log.info(
        "submit_offer_activity.start",
        rental_search_id=rental_search_id,
        listing_id=selected_listing_id,
    )
    _ = uuid.UUID(selected_listing_id)  # validate shape; fail loudly if malformed
    raise NotImplementedError(
        "Offer submission composes the verified outreach tools against the "
        "approved listing's landlord; pending the outreach step."
    )


@activity.defn
async def coordinate_lease_activity(
    rental_search_id: str, selected_listing_id: str, offer_result: dict[str, Any]
) -> dict[str, Any]:
    """Coordinate lease documentation and signing (DocuSign)."""
    log.info("coordinate_lease_activity.start", rental_search_id=rental_search_id)
    raise NotImplementedError(
        "Lease coordination requires the DocuSign envelope exchange, which is not "
        "yet integrated. LeaseService.record_signed_lease persists the result."
    )
