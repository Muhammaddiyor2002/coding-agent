"""Tests for the MCP server exposing ShrekAgent's tools."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest
from mcp import types as mcp_types
from mcp.shared.memory import create_connected_server_and_client_session

from shrek_agent.config import Config
from shrek_agent.mcp_server import build_server


def _run(coro_factory):  # type: ignore[no-untyped-def]
    """Run an async test body via anyio (avoids needing pytest-asyncio)."""
    return anyio.run(coro_factory)


def test_list_tools_exposes_all_six(workspace: Path) -> None:
    """``list_tools`` should advertise every built-in tool with a JSON Schema."""
    config = Config(api_key=None, model="m", max_tokens=128, workspace=workspace)
    server = build_server(config=config)

    async def body() -> None:
        async with create_connected_server_and_client_session(server) as session:
            result = await session.list_tools()
            names = [t.name for t in result.tools]
            assert names == [
                "read_file",
                "list_files",
                "search_files",
                "edit_file",
                "write_file",
                "run_bash",
            ]
            # Every tool advertises a JSON Schema with at least a "type" key.
            for tool in result.tools:
                assert tool.inputSchema.get("type") == "object"
                assert tool.description

    _run(body)


def test_call_tool_round_trip(workspace: Path) -> None:
    """``call_tool`` should invoke the matching ShrekAgent tool and return text."""
    (workspace / "hello.py").write_text("print('hi')\n", encoding="utf-8")
    config = Config(api_key=None, model="m", max_tokens=128, workspace=workspace)
    server = build_server(config=config)

    async def body() -> None:
        async with create_connected_server_and_client_session(server) as session:
            result = await session.call_tool("read_file", {"path": "hello.py"})

            assert result.isError is False
            assert len(result.content) == 1
            block = result.content[0]
            assert isinstance(block, mcp_types.TextContent)
            assert block.text == "print('hi')\n"

    _run(body)


def test_call_tool_surfaces_tool_error_without_crashing(workspace: Path) -> None:
    """Tool errors (e.g. file-not-found) should be returned as text, not raised."""
    config = Config(api_key=None, model="m", max_tokens=128, workspace=workspace)
    server = build_server(config=config)

    async def body() -> None:
        async with create_connected_server_and_client_session(server) as session:
            result = await session.call_tool("read_file", {"path": "does-not-exist.py"})

            # The MCP SDK marks the call as an error when the tool reports
            # one, but the session itself stays alive.
            assert len(result.content) == 1
            block = result.content[0]
            assert isinstance(block, mcp_types.TextContent)
            assert "file not found" in block.text

    _run(body)


def test_call_tool_blocks_path_outside_workspace(workspace: Path, tmp_path: Path) -> None:
    """The workspace sandbox must still be enforced through the MCP server."""
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    config = Config(api_key=None, model="m", max_tokens=128, workspace=workspace)
    server = build_server(config=config)

    async def body() -> None:
        async with create_connected_server_and_client_session(server) as session:
            result = await session.call_tool("read_file", {"path": str(outside)})
            block = result.content[0]
            assert isinstance(block, mcp_types.TextContent)
            assert "outside the workspace" in block.text

    _run(body)


def test_call_tool_unknown_name_raises(workspace: Path) -> None:
    """Unknown tool names should fail the call (the SDK turns ValueError into an error)."""
    config = Config(api_key=None, model="m", max_tokens=128, workspace=workspace)
    server = build_server(config=config)

    async def body() -> None:
        async with create_connected_server_and_client_session(server) as session:
            result = await session.call_tool("nope_not_a_tool", {})
            assert result.isError is True

    _run(body)


def test_write_then_read_round_trip(workspace: Path) -> None:
    """A typical agent flow: write_file via MCP, then read it back via MCP."""
    config = Config(api_key=None, model="m", max_tokens=128, workspace=workspace)
    server = build_server(config=config)

    async def body() -> None:
        async with create_connected_server_and_client_session(server) as session:
            write_result = await session.call_tool(
                "write_file",
                {"path": "greet.txt", "content": "hello from mcp\n"},
            )
            assert write_result.isError is False

            read_result = await session.call_tool("read_file", {"path": "greet.txt"})
            block = read_result.content[0]
            assert isinstance(block, mcp_types.TextContent)
            assert block.text == "hello from mcp\n"

    _run(body)


def test_build_server_accepts_custom_tools(workspace: Path) -> None:
    """A caller should be able to expose a reduced/custom tool set."""
    from shrek_agent.tools import ReadFileTool

    config = Config(api_key=None, model="m", max_tokens=128, workspace=workspace)
    server = build_server(config=config, tools=[ReadFileTool()])

    async def body() -> None:
        async with create_connected_server_and_client_session(server) as session:
            result = await session.list_tools()
            assert [t.name for t in result.tools] == ["read_file"]

    _run(body)


@pytest.mark.parametrize("tool_name", ["read_file", "edit_file", "write_file"])
def test_input_schema_marks_path_required(workspace: Path, tool_name: str) -> None:
    """JSON Schema must mark the ``path`` argument as required."""
    config = Config(api_key=None, model="m", max_tokens=128, workspace=workspace)
    server = build_server(config=config)

    async def body() -> None:
        async with create_connected_server_and_client_session(server) as session:
            tools = await session.list_tools()
            tool = next(t for t in tools.tools if t.name == tool_name)
            required = tool.inputSchema.get("required") or []
            assert "path" in required

    _run(body)
