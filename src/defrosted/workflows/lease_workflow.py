"""
Lease coordination child workflow.

Runs after the user approves and the landlord accepts: it coordinates the lease
document exchange and waits (durably) for signing to complete. Kept as its own
workflow because signing can take days and benefits from independent retry and
visibility.
"""
from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from ..activities import coordinate_lease_activity


@workflow.defn
class LeaseWorkflow:
    @workflow.run
    async def run(self, rental_search_id: str, selected_listing_id: str, offer_result: dict) -> dict:
        return await workflow.execute_activity(
            coordinate_lease_activity,
            args=[rental_search_id, selected_listing_id, offer_result],
            start_to_close_timeout=timedelta(hours=48),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )
