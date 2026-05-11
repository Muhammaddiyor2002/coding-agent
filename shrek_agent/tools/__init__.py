"""Tools the agent can call. Each tool is a small, focused, idempotent operation."""

from __future__ import annotations

from shrek_agent.tools.base import Tool, ToolContext, ToolError
from shrek_agent.tools.edit_file import EditFileTool
from shrek_agent.tools.list_files import ListFilesTool
from shrek_agent.tools.read_file import ReadFileTool
from shrek_agent.tools.run_bash import RunBashTool
from shrek_agent.tools.search_files import SearchFilesTool
from shrek_agent.tools.write_file import WriteFileTool


def default_tools() -> list[Tool]:
    """Return the default tool-set in the order Claude sees them."""
    return [
        ReadFileTool(),
        ListFilesTool(),
        SearchFilesTool(),
        EditFileTool(),
        WriteFileTool(),
        RunBashTool(),
    ]


__all__ = [
    "EditFileTool",
    "ListFilesTool",
    "ReadFileTool",
    "RunBashTool",
    "SearchFilesTool",
    "Tool",
    "ToolContext",
    "ToolError",
    "WriteFileTool",
    "default_tools",
]
