"""
Phone-call tool (Bland.ai).

When email and SMS both fail, the agent places a call. We hand Bland a task
prompt describing what to ask the landlord; Bland's voice model runs the call
and we poll for the transcript/outcome.

We talk to Bland over its REST API with httpx (async) rather than pulling in a
heavy SDK, keeping the dependency surface small.

Verify():
  Poll GET /v1/calls/{call_id} until status is "completed" (success) or one of
  the terminal failure statuses. A call that never connects is a failure so the
  orchestrator can fall back or mark the landlord a ghost.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ...config import Settings
from .base import AgentTool, ToolResult

BLAND_BASE_URL = "https://api.bland.ai/v1"


class VoiceOutreachTool(AgentTool):

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.bland_ai_api_key
        self._headers = {"Authorization": self._api_key}

    @property
    def tool_name(self) -> str:
        return "call_landlord"

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        required = ["landlord_phone", "task"]
        missing = [k for k in required if k not in params]
        if missing:
            raise ValueError(
                f"VoiceOutreachTool.execute() missing required params: {missing}. "
                f"Got: {list(params.keys())}"
            )

        payload = {
            "phone_number": params["landlord_phone"],
            "task": params["task"],
            "voice": params.get("voice", "nat"),
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{BLAND_BASE_URL}/calls", json=payload, headers=self._headers
                )
        except httpx.HTTPError as exc:
            return ToolResult(
                success=False,
                message=f"Bland.ai request error: {exc}",
                data={"error": str(exc)},
                provider_reference=None,
            )

        if response.status_code != 200:
            return ToolResult(
                success=False,
                message=f"Bland.ai rejected the call: HTTP {response.status_code}",
                data={"status_code": response.status_code, "body": response.text},
                provider_reference=None,
            )

        call_id = response.json().get("call_id")
        if not call_id:
            return ToolResult(
                success=False,
                message="Bland.ai returned 200 but no call_id. Cannot verify.",
                data={"body": response.json()},
                provider_reference=None,
            )

        return ToolResult(
            success=True,
            message=f"Call placed with Bland.ai. Call ID: {call_id}",
            data={"to": params["landlord_phone"]},
            provider_reference=call_id,
        )

    async def verify(self, provider_reference: str) -> bool:
        terminal_success = {"completed"}
        terminal_failure = {"failed", "no-answer", "busy", "canceled"}
        max_attempts = 10
        poll_interval_seconds = 30

        for _attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{BLAND_BASE_URL}/calls/{provider_reference}",
                        headers=self._headers,
                    )
                status = response.json().get("status", "")
                if status in terminal_success:
                    return True
                if status in terminal_failure:
                    return False
            except httpx.HTTPError:
                pass  # transient — retry
            await asyncio.sleep(poll_interval_seconds)

        return False

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.tool_name,
            "description": (
                "Place a phone call to a landlord on behalf of the renter. "
                "Use only after email and SMS have failed. Provide a clear task "
                "describing what to confirm (availability, rent, move-in date)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "landlord_phone": {"type": "string", "description": "Landlord phone in E.164 format"},
                    "task": {"type": "string", "description": "What the call should accomplish."},
                },
                "required": ["landlord_phone", "task"],
            },
        }
