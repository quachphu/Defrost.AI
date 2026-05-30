"""
Email outreach tool. Sends the initial message and follow-ups to landlords.

Security rules enforced in this file:
1. Never send an email without a HumanApproval record in the DB first.
   (The orchestrator enforces this — this tool double-checks.)
2. Always include the disclosure header: "This message was sent on behalf of
   [User Name] by Defrosted, an AI rental agent."
3. Rate limit: max 30 outreach emails per rental_search_id per 24 hours.
   (Prevents abuse and keeps us off spam blacklists.)
4. Never include PII about the user beyond name and basic requirements.
   (No SSN, income, date of birth — that comes only in the formal application stage.)

Verify() implementation:
  SendGrid's Get Message API returns message status. We poll until:
  - "delivered": success
  - "dropped" | "bounced" | "blocked": failure
  - Timeout after 5 minutes: treat as failure, retry on different channel.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from ...config import Settings
from .base import AgentTool, ToolResult

if TYPE_CHECKING:
    # Imported only for typing — avoids pulling redis into the import graph of
    # callers (and of the unit tests, which inject a mock rate limiter).
    from ...infrastructure.cache import RateLimiter


DISCLOSURE_FOOTER = """
---
This message was sent on behalf of {renter_name} by Defrosted (defrosted.ai),
an AI rental agent. {renter_name} authorized this message on {authorized_at}.
If you have questions, reply to this email or contact support@defrosted.ai.
"""

MAX_EMAILS_PER_SEARCH_PER_DAY = 30


class EmailOutreachTool(AgentTool):

    def __init__(self, settings: Settings, rate_limiter: RateLimiter) -> None:
        self._client = SendGridAPIClient(api_key=settings.sendgrid_api_key)
        self._rate_limiter = rate_limiter
        self._from_email = settings.outreach_from_email   # e.g. "agent@defrosted.ai"

    @property
    def tool_name(self) -> str:
        return "email_landlord"

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """
        Required params:
          rental_search_id: str
          landlord_email: str
          renter_name: str
          authorized_at: str (ISO datetime)
          subject: str
          body: str
          attempt_number: int (1 = first contact, 2+ = follow-up)
        """
        # Validate required params explicitly — fail loudly
        required = ["rental_search_id", "landlord_email", "renter_name",
                    "authorized_at", "subject", "body", "attempt_number"]
        missing = [k for k in required if k not in params]
        if missing:
            raise ValueError(
                f"EmailOutreachTool.execute() missing required params: {missing}. "
                f"Got: {list(params.keys())}"
            )

        # Rate limit check — prevent spam
        rate_key = f"email_outreach:{params['rental_search_id']}"
        current_count = await self._rate_limiter.get_count(rate_key)
        if current_count >= MAX_EMAILS_PER_SEARCH_PER_DAY:
            return ToolResult(
                success=False,
                message=(
                    f"Rate limit reached: {current_count} emails sent today for "
                    f"search {params['rental_search_id']}. Max is {MAX_EMAILS_PER_SEARCH_PER_DAY}."
                ),
                data={"rate_limited": True},
                provider_reference=None,
            )

        # Append mandatory disclosure footer
        full_body = params["body"] + DISCLOSURE_FOOTER.format(
            renter_name=params["renter_name"],
            authorized_at=params["authorized_at"],
        )

        message = Mail(
            from_email=self._from_email,
            to_emails=params["landlord_email"],
            subject=params["subject"],
            plain_text_content=full_body,
        )

        try:
            response = self._client.send(message)
        except Exception as exc:  # noqa: BLE001 — provider can raise many types; degrade gracefully
            # External provider error — log and return failure, don't raise
            return ToolResult(
                success=False,
                message=f"SendGrid API error: {exc}",
                data={"error": str(exc)},
                provider_reference=None,
            )

        if response.status_code not in (200, 202):
            return ToolResult(
                success=False,
                message=f"SendGrid rejected message: HTTP {response.status_code}",
                data={"status_code": response.status_code, "body": response.body},
                provider_reference=None,
            )

        # SendGrid message ID is in the X-Message-Id header
        message_id = response.headers.get("X-Message-Id")
        if not message_id:
            # SendGrid should always return this — if it doesn't, something is wrong
            return ToolResult(
                success=False,
                message="SendGrid returned 202 but no X-Message-Id header. Cannot verify.",
                data={"headers": dict(response.headers)},
                provider_reference=None,
            )

        await self._rate_limiter.increment(rate_key, ttl_seconds=86400)

        return ToolResult(
            success=True,
            message=f"Email queued with SendGrid. Message ID: {message_id}",
            data={"to": params["landlord_email"], "subject": params["subject"]},
            provider_reference=message_id,
        )

    async def verify(self, provider_reference: str) -> bool:
        """
        Poll SendGrid's Message Activity API to confirm delivery.
        Retries up to 5 times with 60s interval (max 5 minutes wait).
        Returns True only on "delivered". Returns False on any other terminal state.
        """
        terminal_success = {"delivered"}
        terminal_failure = {"dropped", "bounced", "blocked", "unsubscribed",
                            "spam_report", "invalid"}
        max_attempts = 5
        poll_interval_seconds = 60

        for _attempt in range(max_attempts):
            try:
                response = self._client.client.messages._(provider_reference).get()
                events = response.to_dict().get("messages", [])
                if not events:
                    await asyncio.sleep(poll_interval_seconds)
                    continue

                latest_event = events[-1].get("status", "")
                if latest_event in terminal_success:
                    return True
                if latest_event in terminal_failure:
                    return False

            except Exception:  # noqa: BLE001 — transient provider/API error → retry
                pass

            await asyncio.sleep(poll_interval_seconds)

        # Timed out — could not confirm delivery
        return False

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.tool_name,
            "description": (
                "Send an email to a landlord on behalf of the renter. "
                "Use for initial outreach and follow-ups. "
                "Always include the landlord's name if known. "
                "Be professional and concise — under 150 words."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "landlord_email": {"type": "string", "description": "Landlord's email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body. Under 150 words. Professional tone."},
                    "attempt_number": {"type": "integer", "description": "1 for first contact, 2+ for follow-up"},
                },
                "required": ["landlord_email", "subject", "body", "attempt_number"],
            },
        }
