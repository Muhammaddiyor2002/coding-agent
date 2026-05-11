"""Base classes for ShrekAgent tools."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel

from shrek_agent.config import Config


class ToolError(Exception):
    """Raised by a tool when execution fails in a user-visible way."""


@dataclass(slots=True)
class ToolContext:
    """Execution context passed to every tool invocation."""

    config: Config

    @property
    def workspace(self) -> Path:
        return self.config.workspace

    def resolve(self, raw_path: str) -> Path:
        """Resolve ``raw_path`` against the workspace and ensure it stays inside it.

        Raises ``ToolError`` if the path attempts to escape the workspace via ``..``
        or absolute paths pointing elsewhere.
        """
        if not raw_path:
            raise ToolError("path must not be empty")

        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = self.workspace / candidate

        resolved = candidate.resolve()
        workspace = self.workspace.resolve()
        try:
            resolved.relative_to(workspace)
        except ValueError as exc:
            raise ToolError(f"refusing to touch path outside the workspace: {raw_path!r}") from exc
        return resolved

    def relpath(self, path: Path) -> str:
        """Return ``path`` relative to the workspace, for display purposes."""
        try:
            return os.path.relpath(path, self.workspace)
        except ValueError:
            return str(path)


class Tool(ABC):
    """Abstract base class for a Claude-callable tool."""

    name: ClassVar[str]
    description: ClassVar[str]
    InputModel: ClassVar[type[BaseModel]]

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return the JSON schema Claude uses to validate calls."""
        return self.InputModel.model_json_schema()

    def parse(self, raw_input: dict[str, Any]) -> BaseModel:
        """Validate and coerce raw arguments using the tool's input model."""
        return self.InputModel.model_validate(raw_input)

    @abstractmethod
    def run(self, args: BaseModel, ctx: ToolContext) -> str:
        """Execute the tool. Return a plain-text result for Claude.

        Tools should raise ``ToolError`` for expected failures (e.g. "file not found");
        unexpected exceptions are caught by the agent and surfaced verbatim.
        """

    def call_summary(self, args: BaseModel) -> str:
        """One-line description of *what* this call will do — shown in the terminal."""
        return ", ".join(f"{k}={v!r}" for k, v in args.model_dump().items())


def to_claude_tool(tool: Tool) -> dict[str, Any]:
    """Convert a :class:`Tool` into the dict shape the Anthropic SDK expects."""
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }
