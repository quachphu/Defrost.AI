"""
SMS follow-up tool (Twilio).

Used when email goes unanswered and we have a landlord phone number. Same
guard rails as email: a per-search daily rate limit and the disclosure line
(SMS is short, so the disclosure is a single trailing sentence).

Twilio's SDK is synchronous; we run its blocking calls in a thread so we don't
stall the event loop.

Verify():
  Fetch the message by SID and check Twilio's delivery status. "delivered" is
  success; "undelivered"/"failed" are terminal failures; anything else is still
  in flight, so we poll a few times before giving up.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from twilio.rest import Client

from ...config import Settings
from .base import AgentTool, ToolResult

if TYPE_CHECKING:
    from ...infrastructure.cache import RateLimiter

DISCLOSURE_SUFFIX = " — Sent by Defrosted (defrosted.ai), an AI rental agent, on behalf of {renter_name}."
MAX_SMS_PER_SEARCH_PER_DAY = 30


class SmsOutreachTool(AgentTool):

    def __init__(self, settings: Settings, rate_limiter: RateLimiter) -> None:
        self._client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        self._rate_limiter = rate_limiter
        self._from_number = settings.twilio_phone_number

    @property
    def tool_name(self) -> str:
        return "sms_landlord"

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        required = ["rental_search_id", "landlord_phone", "renter_name", "body"]
        missing = [k for k in required if k not in params]
        if missing:
            raise ValueError(
                f"SmsOutreachTool.execute() missing required params: {missing}. "
                f"Got: {list(params.keys())}"
            )

        rate_key = f"sms_outreach:{params['rental_search_id']}"
        if await self._rate_limiter.get_count(rate_key) >= MAX_SMS_PER_SEARCH_PER_DAY:
            return ToolResult(
                success=False,
                message=f"SMS rate limit reached for search {params['rental_search_id']}.",
                data={"rate_limited": True},
                provider_reference=None,
            )

        body = params["body"] + DISCLOSURE_SUFFIX.format(renter_name=params["renter_name"])

        try:
            message = await asyncio.to_thread(
                self._client.messages.create,
                to=params["landlord_phone"],
                from_=self._from_number,
                body=body,
            )
        except Exception as exc:  # noqa: BLE001 — provider error → degrade gracefully
            return ToolResult(
                success=False,
                message=f"Twilio API error: {exc}",
                data={"error": str(exc)},
                provider_reference=None,
            )

        await self._rate_limiter.increment(rate_key, ttl_seconds=86400)
        return ToolResult(
            success=True,
            message=f"SMS queued with Twilio. SID: {message.sid}",
            data={"to": params["landlord_phone"]},
            provider_reference=message.sid,
        )

    async def verify(self, provider_reference: str) -> bool:
        terminal_success = {"delivered"}
        terminal_failure = {"undelivered", "failed"}
        max_attempts = 5
        poll_interval_seconds = 30

        for _attempt in range(max_attempts):
            try:
                message = await asyncio.to_thread(
                    self._client.messages(provider_reference).fetch
                )
                if message.status in terminal_success:
                    return True
                if message.status in terminal_failure:
                    return False
            except Exception:  # noqa: BLE001 — transient API error → retry
                pass
            await asyncio.sleep(poll_interval_seconds)

        return False

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.tool_name,
            "description": (
                "Send a short SMS to a landlord on behalf of the renter. "
                "Use only after email has gone unanswered. Keep under 320 characters."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "landlord_phone": {"type": "string", "description": "Landlord phone in E.164 format"},
                    "body": {"type": "string", "description": "SMS body. Under 320 characters."},
                },
                "required": ["landlord_phone", "body"],
            },
        }
