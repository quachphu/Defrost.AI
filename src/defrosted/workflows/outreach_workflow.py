"""
Per-listing outreach child workflow.

Encapsulates the contact → wait → follow-up → escalate loop for a single
listing so the parent RentalSearchWorkflow can fan these out in parallel (one
child per listing) and let Temporal track each independently.

Escalation order: email → (no reply in 24h) follow-up email →
(no reply in 24h) SMS → (no reply) phone → mark ghost.
"""
from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from ..activities import contact_landlords_activity, wait_for_responses_activity

# Hours to wait for a reply before the next escalation step.
FOLLOW_UP_INTERVAL_HOURS = 24
MAX_ATTEMPTS = 4


@workflow.defn
class OutreachWorkflow:
    @workflow.run
    async def run(self, rental_search_id: str, listing: dict) -> dict:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            await workflow.execute_activity(
                contact_landlords_activity,
                args=[rental_search_id, [listing]],
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

            confirmed = await workflow.execute_activity(
                wait_for_responses_activity,
                args=[rental_search_id, [{"listing": listing, "attempt": attempt}]],
                start_to_close_timeout=timedelta(hours=FOLLOW_UP_INTERVAL_HOURS),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            if confirmed:
                return {"status": "responded", "attempts": attempt, "confirmed": confirmed}

        return {"status": "ghost", "attempts": MAX_ATTEMPTS}
