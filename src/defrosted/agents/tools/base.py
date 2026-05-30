"""
AgentTool base interface.

Every tool the LLM agent can call implements this interface.
The critical design decision: every tool has a verify() method.

Why verify() is non-negotiable:
  The Replit incident (July 2025) — an AI agent deleted a production database
  and then reported success. It fabricated confirmations. If your agent says
  "I sent the email," you verify it against SendGrid's API before recording
  the action. Never trust the LLM's self-report.

  In this system: the LLM calls a tool → the tool calls the external provider
  → the tool calls verify() against the provider's API → only if verify()
  returns True does the action get recorded as an event in the event store.

Karpathy rule: this interface is small and explicit. 4 methods. That's it.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """
    What every tool returns. Success or failure with a clear message.
    provider_reference: the external system's ID for this action
                        (SendGrid message ID, Twilio SID, Bland call ID)
                        Used by verify() to confirm the action happened.
    """
    success: bool
    message: str
    data: dict[str, Any]
    provider_reference: str | None = None   # None if action didn't reach provider


class AgentTool(ABC):
    """
    Every agent tool implements these 4 methods. Nothing more.

    tool_name:  human-readable name for logging and the agent's tool registry
    execute():  call the external provider, return ToolResult
    verify():   call the provider's API to confirm the action happened
                Returns True only if the provider confirms success.
                Called automatically by the orchestrator — tools never skip it.
    describe(): returns the function schema for LLM tool calling
    """

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Unique name used in LLM tool call schemas and log messages."""
        ...

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """
        Execute the action. May succeed or fail — always returns ToolResult.
        Never raises an exception for external failures (provider down, rate limit).
        Raise only for programming errors (missing required param, wrong type).
        """
        ...

    @abstractmethod
    async def verify(self, provider_reference: str) -> bool:
        """
        Confirm with the external provider that the action succeeded.
        Called by the orchestrator AFTER execute() returns success.

        provider_reference: the ID from execute()'s ToolResult.provider_reference
        Returns: True if provider confirms action happened, False otherwise.
        """
        ...

    @abstractmethod
    def describe(self) -> dict[str, Any]:
        """
        Returns the LLM function calling schema for this tool.
        Used by the orchestrator to build the tools list for the Claude API call.
        """
        ...
