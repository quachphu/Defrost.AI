"""
Server-side action verification.

This is the enforcement point for the rule: never trust the LLM's self-report.
A tool's ``execute`` returning success only means the provider *accepted* the
request. We do not record a domain event until ``verify`` confirms the action
actually happened against the provider's own API.

Flow:
    result = await tool.execute(params)
    if not result.success: ...handle, do NOT record...
    verified = await tool.verify(result.provider_reference)
    if verified: ...record the event...
    else: ...treat as failure, try another channel...

Karpathy rule: one function, one job. This module decides "did it really happen,
and if so, write the immutable record" — nothing else.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import structlog

from ..domain.events import OutreachSentEvent
from ..infrastructure.event_store import EventStore
from .tools.base import AgentTool, ToolResult

log = structlog.get_logger(__name__)


async def verify_and_record_outreach(
    tool: AgentTool,
    result: ToolResult,
    *,
    event_store: EventStore,
    rental_search_id: uuid.UUID,
    outreach_attempt_id: uuid.UUID,
    listing_id: uuid.UUID,
    landlord_id: uuid.UUID,
    channel: str,
) -> bool:
    """
    Verify an outreach action with its provider and, only if confirmed, append an
    OutreachSentEvent. Returns True iff the action was verified and recorded.
    """
    if not result.success or result.provider_reference is None:
        log.info(
            "outreach_not_recorded_execute_failed",
            tool=tool.tool_name,
            rental_search_id=str(rental_search_id),
            message=result.message,
        )
        return False

    verified = await tool.verify(result.provider_reference)
    if not verified:
        log.warning(
            "outreach_not_recorded_verify_failed",
            tool=tool.tool_name,
            rental_search_id=str(rental_search_id),
            provider_reference=result.provider_reference,
        )
        return False

    await event_store.append(
        OutreachSentEvent(
            rental_search_id=rental_search_id,
            sequence=0,  # event store assigns the real sequence
            outreach_attempt_id=outreach_attempt_id,
            listing_id=listing_id,
            landlord_id=landlord_id,
            channel=channel,
            provider_message_id=result.provider_reference,
            verified_sent_at=datetime.utcnow(),
        )
    )
    log.info(
        "outreach_recorded",
        tool=tool.tool_name,
        rental_search_id=str(rental_search_id),
        provider_reference=result.provider_reference,
    )
    return True
