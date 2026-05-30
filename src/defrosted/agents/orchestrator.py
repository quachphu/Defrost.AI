"""
Agent orchestrator — the LangGraph state machine that runs one verified
tool-use loop with Claude.

The graph has exactly two nodes and one decision:

    call_model ──(assistant asked for a tool?)──► execute_tools ──► call_model
        │
        └──(no tool calls)──► END

The non-negotiable detail lives in ``execute_tools``: after a tool runs we call
``tool.verify(...)`` and feed the *verified* outcome back to the model. The
model never gets to assume a tool succeeded — it is told whether the provider
actually confirmed it (Karpathy: never trust the LLM's self-report).

Heavy imports (langgraph, anthropic) are top-level: this module is only loaded
inside Temporal activities / workers that have the ``infra`` extra installed.
"""
from __future__ import annotations

from typing import Any, TypedDict

import structlog
from anthropic import AsyncAnthropic
from langgraph.graph import END, StateGraph

from ..config import Settings
from .tools.base import AgentTool

log = structlog.get_logger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-20250514"
COMPLEX_MODEL = "claude-opus-4-8"
MAX_TOKENS = 2048


class AgentState(TypedDict):
    # The running Anthropic message list (user/assistant turns + tool results).
    messages: list[dict[str, Any]]
    # Set True once the model produces a turn with no tool calls.
    done: bool


class AgentOrchestrator:
    """
    Runs a tool-using Claude agent to completion over a registry of AgentTools.

    Usage:
        orch = AgentOrchestrator(settings, tools=[email_tool, sms_tool])
        final_messages = await orch.run(system_prompt, user_prompt)
    """

    def __init__(
        self,
        settings: Settings,
        tools: list[AgentTool],
        *,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._tools_by_name: dict[str, AgentTool] = {t.tool_name: t for t in tools}
        self._tool_schemas = [t.describe() for t in tools]
        self._model = model
        self._system_prompt: str | None = None
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        graph = StateGraph(AgentState)
        graph.add_node("call_model", self._call_model)
        graph.add_node("execute_tools", self._execute_tools)
        graph.set_entry_point("call_model")
        graph.add_conditional_edges(
            "call_model",
            lambda state: "execute_tools" if not state["done"] else END,
        )
        graph.add_edge("execute_tools", "call_model")
        return graph.compile()

    async def _call_model(self, state: AgentState) -> AgentState:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            system=self._system_prompt or "",
            messages=state["messages"],
            tools=self._tool_schemas,
        )
        assistant_content = [block.model_dump() for block in response.content]
        state["messages"].append({"role": "assistant", "content": assistant_content})
        tool_calls = [b for b in assistant_content if b.get("type") == "tool_use"]
        state["done"] = len(tool_calls) == 0
        return state

    async def _execute_tools(self, state: AgentState) -> AgentState:
        last = state["messages"][-1]["content"]
        tool_results: list[dict[str, Any]] = []
        for block in last:
            if block.get("type") != "tool_use":
                continue
            tool = self._tools_by_name.get(block["name"])
            if tool is None:
                tool_results.append(self._tool_error(block["id"], f"unknown tool {block['name']}"))
                continue

            result = await tool.execute(block["input"])
            verified = False
            if result.success and result.provider_reference is not None:
                verified = await tool.verify(result.provider_reference)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "is_error": not (result.success and verified),
                "content": (
                    f"{result.message} (verified={verified})"
                    if result.success
                    else result.message
                ),
            })
            log.info(
                "tool_executed",
                tool=tool.tool_name,
                success=result.success,
                verified=verified,
            )

        state["messages"].append({"role": "user", "content": tool_results})
        return state

    @staticmethod
    def _tool_error(tool_use_id: str, message: str) -> dict[str, Any]:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "is_error": True,
            "content": message,
        }

    async def run(self, system_prompt: str, user_prompt: str) -> list[dict[str, Any]]:
        """Run the agent to completion and return the full message history."""
        self._system_prompt = system_prompt
        initial: AgentState = {
            "messages": [{"role": "user", "content": user_prompt}],
            "done": False,
        }
        final_state: AgentState = await self._graph.ainvoke(initial)
        return final_state["messages"]
