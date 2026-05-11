"""Core agent loop: send user input to Claude, dispatch tool calls, repeat."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from pydantic import ValidationError

from shrek_agent.config import Config
from shrek_agent.console import (
    render_assistant,
    render_info,
    render_tool_call,
    render_tool_error,
)
from shrek_agent.prompts import SYSTEM_PROMPT
from shrek_agent.tools import default_tools
from shrek_agent.tools.base import Tool, ToolContext, ToolError, to_claude_tool

if TYPE_CHECKING:
    from anthropic import Anthropic


MAX_TOOL_ITERATIONS = 20


@dataclass
class Agent:
    config: Config
    client: Anthropic
    tools: list[Tool] = field(default_factory=default_tools)
    conversation: list[dict[str, Any]] = field(default_factory=list)
    system_prompt: str = SYSTEM_PROMPT

    @property
    def tool_context(self) -> ToolContext:
        return ToolContext(config=self.config)

    @property
    def tool_map(self) -> dict[str, Tool]:
        return {t.name: t for t in self.tools}

    def reset(self) -> None:
        """Clear conversation history."""
        self.conversation.clear()

    def history_json(self) -> str:
        """Return a JSON dump of the current conversation suitable for /save."""
        return json.dumps(self.conversation, indent=2, default=_jsonable)

    def load_history(self, blob: str) -> None:
        data = json.loads(blob)
        if not isinstance(data, list):
            raise ValueError("history file must contain a JSON list of messages")
        self.conversation = data

    def send(self, user_input: str) -> None:
        """Send a user message and process Claude's response, including tool calls."""
        self.conversation.append(
            {"role": "user", "content": [{"type": "text", "text": user_input}]}
        )

        for _ in range(MAX_TOOL_ITERATIONS):
            message = self._call_claude()
            self.conversation.append(
                {"role": "assistant", "content": _content_to_param(message.content)}
            )

            tool_results: list[dict[str, Any]] = []
            for block in message.content:
                btype = getattr(block, "type", None)
                if btype == "text":
                    render_assistant(getattr(block, "text", ""))
                elif btype == "tool_use":
                    tool_results.append(self._execute_tool_block(block))

            if not tool_results:
                return

            self.conversation.append({"role": "user", "content": tool_results})

        # Hit the iteration cap mid-tool-loop: the last appended message is a
        # user (tool_results). Append a synthetic assistant text so the next
        # send() starts from a valid alternating state and Claude is told what
        # happened (instead of getting a 400 on the next call).
        limit_note = "[stopped: reached the agent's tool-call iteration limit]"
        render_info("⚠ stopping: reached tool-call iteration limit")
        self.conversation.append(
            {
                "role": "assistant",
                "content": [{"type": "text", "text": limit_note}],
            }
        )

    # ---- internals ---------------------------------------------------------

    def _call_claude(self) -> Any:
        return self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=self.system_prompt,
            messages=cast(Any, self.conversation),
            tools=cast(Any, [to_claude_tool(t) for t in self.tools]),
        )

    def _execute_tool_block(self, block: Any) -> dict[str, Any]:
        tool_id: str = block.id
        name: str = block.name
        raw_input: dict[str, Any] = block.input or {}

        tool = self.tool_map.get(name)
        if tool is None:
            render_tool_error(name, "unknown tool")
            return _tool_result(tool_id, f"tool {name!r} is not registered", is_error=True)

        try:
            args = tool.parse(raw_input)
        except ValidationError as exc:
            render_tool_error(name, f"bad arguments: {exc.error_count()} error(s)")
            return _tool_result(tool_id, str(exc), is_error=True)

        render_tool_call(name, tool.call_summary(args))

        try:
            result = tool.run(args, self.tool_context)
        except ToolError as exc:
            render_tool_error(name, str(exc))
            return _tool_result(tool_id, str(exc), is_error=True)
        except Exception as exc:
            render_tool_error(name, f"unhandled: {exc}")
            return _tool_result(tool_id, f"unhandled error: {exc}", is_error=True)

        return _tool_result(tool_id, result, is_error=False)


def _tool_result(tool_id: str, content: str, *, is_error: bool) -> dict[str, Any]:
    return {
        "type": "tool_result",
        "tool_use_id": tool_id,
        "content": content,
        "is_error": is_error,
    }


def _content_to_param(content: Iterable[Any]) -> list[dict[str, Any]]:
    """Convert SDK content blocks into plain-dict form for re-sending."""
    out: list[dict[str, Any]] = []
    for block in content:
        btype = getattr(block, "type", None)
        if btype == "text":
            out.append({"type": "text", "text": block.text})
        elif btype == "tool_use":
            out.append(
                {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                }
            )
        elif btype == "thinking":
            out.append({"type": "thinking", "thinking": getattr(block, "thinking", "")})
    return out


def _jsonable(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return str(obj)
