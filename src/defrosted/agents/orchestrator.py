"""
Agent orchestrator — the LangGraph state machine that runs one verified
tool-use loop with Groq (free tier, OpenAI-compatible API).

The graph has exactly two nodes and one decision:

    call_model ──(assistant asked for a tool?)──► execute_tools ──► call_model
        │
        └──(no tool calls)──► END

The non-negotiable detail lives in ``execute_tools``: after a tool runs we call
``tool.verify(...)`` and feed the *verified* outcome back to the model. The
model never gets to assume a tool succeeded — it is told whether the provider
actually confirmed it (Karpathy: never trust the LLM's self-report).

Groq uses the OpenAI message/tool format which differs from Anthropic's:
  - Tools schemas: {"type": "function", "function": {...}}  (not {"name":..., "input_schema":...})
  - Tool calls come back on choice.message.tool_calls  (not content blocks)
  - Tool results go in as role="tool" messages  (not role="user" content blocks)

_to_openai_schema() converts the existing Anthropic-format describe() output
from each AgentTool so no tool implementations need to change.
"""
from __future__ import annotations

import json
from typing import Any, TypedDict

import structlog
from groq import AsyncGroq
from langgraph.graph import END, StateGraph

from ..config import Settings
from .tools.base import AgentTool

log = structlog.get_logger(__name__)

# llama-3.3-70b-versatile: confirmed working tool calling on Groq free tier.
# openai/gpt-oss-20b also works (faster, smaller). gpt-oss-120b does not call tools.
DEFAULT_MODEL = "llama-3.3-70b-versatile"
COMPLEX_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 2048


class AgentState(TypedDict):
    # The running message list in OpenAI format (user/assistant/tool turns).
    messages: list[dict[str, Any]]
    # Set True once the model produces a turn with no tool calls.
    done: bool


class AgentOrchestrator:
    """
    Runs a tool-using Groq agent to completion over a registry of AgentTools.

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
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._tools_by_name: dict[str, AgentTool] = {t.tool_name: t for t in tools}
        # Convert from Anthropic describe() format → OpenAI/Groq format
        self._tool_schemas = [self._to_openai_schema(t.describe()) for t in tools]
        self._model = model
        self._system_prompt: str | None = None
        self._graph = self._build_graph()

    @staticmethod
    def _to_openai_schema(anthropic_schema: dict[str, Any]) -> dict[str, Any]:
        """
        AgentTool.describe() returns Anthropic format:
          {"name": ..., "description": ..., "input_schema": {...}}

        Groq/OpenAI expects:
          {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}
        """
        return {
            "type": "function",
            "function": {
                "name": anthropic_schema["name"],
                "description": anthropic_schema.get("description", ""),
                "parameters": anthropic_schema.get(
                    "input_schema", {"type": "object", "properties": {}}
                ),
            },
        }

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
        # Groq/OpenAI: system prompt is the first message, not a separate param
        full_messages = [
            {"role": "system", "content": self._system_prompt or ""},
            *state["messages"],
        ]

        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            messages=full_messages,
            tools=self._tool_schemas,
            tool_choice="auto",
        )

        choice = response.choices[0]
        msg = choice.message

        # Build assistant message in OpenAI format
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": msg.content,
        }
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]

        state["messages"].append(assistant_msg)
        state["done"] = not bool(msg.tool_calls)
        return state

    async def _execute_tools(self, state: AgentState) -> AgentState:
        last = state["messages"][-1]
        tool_calls = last.get("tool_calls", [])

        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            tool_input: dict[str, Any] = json.loads(tc["function"]["arguments"])
            tool = self._tools_by_name.get(tool_name)

            if tool is None:
                content = f"ERROR: unknown tool {tool_name}"
            else:
                result = await tool.execute(tool_input)
                verified = False
                if result.success and result.provider_reference is not None:
                    verified = await tool.verify(result.provider_reference)

                content = (
                    f"{result.message} (verified={verified})"
                    if result.success
                    else f"ERROR: {result.message}"
                )
                log.info(
                    "tool_executed",
                    tool=tool_name,
                    success=result.success,
                    verified=verified,
                )

            # OpenAI/Groq: each tool result is its own message with role="tool"
            state["messages"].append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": content,
            })

        return state

    async def run(self, system_prompt: str, user_prompt: str) -> list[dict[str, Any]]:
        """Run the agent to completion and return the full message history."""
        self._system_prompt = system_prompt
        initial: AgentState = {
            "messages": [{"role": "user", "content": user_prompt}],
            "done": False,
        }
        final_state: AgentState = await self._graph.ainvoke(initial)
        return final_state["messages"]
