"""
Temporal workflow for a complete rental search.

Why Temporal and not a cron job or Celery task:
A rental search takes hours to days:
  - Browser scraping: 10–30 minutes to collect 50+ listings
  - Landlord outreach: send email, wait 48 hours, follow up, wait 24 more hours
  - Lease signing: wait for DocuSign to complete

Temporal gives us:
  1. Durable execution: if the server crashes at hour 23, the workflow resumes exactly
     where it left off when the server restarts. Zero data loss.
  2. Signals: the workflow pauses at human approval gates and waits for a signal
     (the user's approval) before continuing. Clean and explicit.
  3. Timeouts: each activity has a start-to-close timeout. If an activity hangs,
     Temporal handles the retry logic.
  4. Visibility: every workflow step is visible in the Temporal Web UI with full history.

Architecture:
  - The workflow is the coordinator: it calls activities in sequence.
  - Activities are the workers: each does one thing (scrape, email, verify, etc.)
  - Activities are retryable: Temporal retries failed activities with backoff.
  - The workflow itself is NOT retried: it runs to completion or fails terminally.

Karpathy rule: the workflow reads like a recipe. Top to bottom. No magic.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities — each activity is a simple async function, not a class
with workflow.unsafe.imports_passed_through():
    from ..activities import (
        build_approval_options_activity,
        contact_landlords_activity,
        coordinate_lease_activity,
        deduplicate_listings_activity,
        scrape_listings_activity,
        submit_offer_activity,
        wait_for_responses_activity,
    )


@workflow.defn
class RentalSearchWorkflow:
    """
    Top-level workflow for one renter's housing search.

    Signals (external → workflow):
        user_approved_listing: called when the user selects a listing in the UI

    Queries (read-only, from external):
        get_status: returns current workflow status and progress
    """

    def __init__(self) -> None:
        # Approval signal — set when user approves a listing
        # None = no approval received yet
        self._user_approval: dict | None = None

    @workflow.signal
    def user_approved_listing(self, approval_data: dict) -> None:
        """
        Called by the API when the user selects a listing.
        The workflow is blocking at the approval gate and will resume when this fires.
        """
        self._user_approval = approval_data

    @workflow.query
    def get_status(self) -> dict:
        """Read-only snapshot of current workflow state for the UI."""
        return {
            "has_approval": self._user_approval is not None,
            "approval": self._user_approval,
        }

    @workflow.run
    async def run(self, rental_search_id: str) -> dict:
        """
        The complete rental search pipeline. Reads top to bottom.
        Each step is an activity call with explicit timeout and retry policy.
        """
        _search_id = uuid.UUID(rental_search_id)  # validate shape; fail loudly if malformed

        # ── Step 1: Scrape listings ──────────────────────────────────────────
        # Scraping can take 10–30 minutes. Max 2 retries if it fails.
        listings = await workflow.execute_activity(
            scrape_listings_activity,
            args=[rental_search_id],
            start_to_close_timeout=timedelta(minutes=45),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(minutes=2),
            ),
        )

        if not listings:
            return {"status": "failed", "reason": "no_listings_found"}

        # ── Step 2: Deduplicate ──────────────────────────────────────────────
        unique_listings = await workflow.execute_activity(
            deduplicate_listings_activity,
            args=[rental_search_id, listings],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        # ── Step 3: Contact landlords ────────────────────────────────────────
        # Sends initial outreach to up to 20 unique listings.
        # Returns list of outreach_attempt_ids.
        outreach_results = await workflow.execute_activity(
            contact_landlords_activity,
            args=[rental_search_id, unique_listings],
            start_to_close_timeout=timedelta(hours=2),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        # ── Step 4: Wait for responses ───────────────────────────────────────
        # Poll for landlord responses over 48–72 hours.
        # Sends follow-ups at 24h and 48h if no response.
        # Returns list of listings with confirmed interest from landlord.
        confirmed_listings = await workflow.execute_activity(
            wait_for_responses_activity,
            args=[rental_search_id, outreach_results],
            start_to_close_timeout=timedelta(hours=96),   # up to 4 days
            retry_policy=RetryPolicy(maximum_attempts=1),  # no retry on this one
        )

        if not confirmed_listings:
            return {"status": "failed", "reason": "no_landlord_responses"}

        # ── Step 5: Build approval options and wait for user ─────────────────
        # Present top 3–5 listings to the user.
        # Block here until user_approved_listing signal fires (or 48h timeout).
        await workflow.execute_activity(
            build_approval_options_activity,
            args=[rental_search_id, confirmed_listings],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        # Wait for the human signal — with 48-hour timeout
        await workflow.wait_condition(
            lambda: self._user_approval is not None,
            timeout=timedelta(hours=48),
        )

        if self._user_approval is None:
            # Timed out — user didn't respond
            return {"status": "failed", "reason": "approval_timeout"}

        selected_listing_id = self._user_approval["listing_id"]

        # ── Step 6: Submit offer ─────────────────────────────────────────────
        offer_result = await workflow.execute_activity(
            submit_offer_activity,
            args=[rental_search_id, selected_listing_id, self._user_approval],
            start_to_close_timeout=timedelta(hours=4),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        if not offer_result["accepted"]:
            return {"status": "failed", "reason": "offer_rejected", "details": offer_result}

        # ── Step 7: Coordinate lease ─────────────────────────────────────────
        lease_result = await workflow.execute_activity(
            coordinate_lease_activity,
            args=[rental_search_id, selected_listing_id, offer_result],
            start_to_close_timeout=timedelta(hours=48),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        return {
            "status": "completed",
            "lease_id": lease_result["lease_id"],
            "listing_id": selected_listing_id,
            "signed_at": lease_result["signed_at"],
        }
