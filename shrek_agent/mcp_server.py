"""Expose ShrekAgent's tools over the Model Context Protocol (MCP).

This lets other MCP-aware clients (Claude Desktop, Cursor, Zed, custom IDEs,
etc.) call the same six tools the agent uses internally — `read_file`,
`write_file`, `edit_file`, `list_files`, `search_files`, `run_bash` — against
a sandboxed workspace.

Run it directly:

.. code-block:: bash

    shrek mcp --workspace /path/to/project       # via the main CLI
    shrek-mcp --workspace /path/to/project       # via the dedicated console script

The server speaks JSON-RPC over stdio, which is the transport Claude Desktop
and most desktop MCP hosts use.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import anyio
from mcp import types as mcp_types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from shrek_agent import __version__
from shrek_agent.config import Config
from shrek_agent.tools import Tool, ToolContext, ToolError, default_tools

SERVER_NAME = "shrek-agent"


def build_server(
    config: Config | None = None,
    tools: Iterable[Tool] | None = None,
    *,
    server_name: str = SERVER_NAME,
) -> Server[Any, Any]:
    """Build an MCP :class:`Server` that proxies ShrekAgent's tools.

    Parameters
    ----------
    config:
        Runtime config. Defaults to :meth:`Config.from_env`. The ``workspace``
        field is the sandbox root: every tool path must stay inside it.
    tools:
        Override the tool set. Defaults to :func:`default_tools`. Order is
        preserved in the ``list_tools`` response.
    server_name:
        Name advertised to MCP clients. Defaults to ``"shrek-agent"``.
    """
    cfg = config if config is not None else Config.from_env()
    tools_list: list[Tool] = list(tools) if tools is not None else default_tools()
    registry: dict[str, Tool] = {t.name: t for t in tools_list}
    ctx = ToolContext(config=cfg)

    server: Server[Any, Any] = Server(server_name, version=__version__)

    @server.list_tools()  # type: ignore[no-untyped-call]
    async def _list_tools() -> list[mcp_types.Tool]:
        return [
            mcp_types.Tool(
                name=t.name,
                description=t.description,
                inputSchema=t.input_schema,
            )
            for t in tools_list
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any]) -> list[mcp_types.TextContent]:
        tool = registry.get(name)
        if tool is None:
            raise ValueError(f"unknown tool: {name!r}")

        try:
            parsed = tool.parse(arguments or {})
        except Exception as exc:
            # Invalid arguments should surface as a tool error, not crash the
            # server (the call_tool decorator already validated against the
            # JSON schema, but pydantic does its own coercion as well).
            return [mcp_types.TextContent(type="text", text=f"invalid arguments: {exc}")]

        try:
            # Run the (potentially blocking) tool in a worker thread so we
            # don't stall the MCP event loop on slow `run_bash` calls.
            output = await anyio.to_thread.run_sync(tool.run, parsed, ctx)
        except ToolError as exc:
            return [mcp_types.TextContent(type="text", text=f"error: {exc}")]
        except Exception as exc:  # pragma: no cover - defensive
            return [mcp_types.TextContent(type="text", text=f"unexpected error: {exc!r}")]

        return [mcp_types.TextContent(type="text", text=output)]

    return server


async def serve_stdio_async(server: Server[Any, Any]) -> None:
    """Run ``server`` over stdio until the client disconnects."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def serve_stdio(config: Config | None = None) -> None:
    """Build the MCP server and serve it over stdio (blocking).

    This is the synchronous entry point wired up to the ``shrek mcp``
    subcommand and the ``shrek-mcp`` console script.
    """
    server = build_server(config=config)
    anyio.run(serve_stdio_async, server)


__all__ = ["SERVER_NAME", "build_server", "serve_stdio", "serve_stdio_async"]


if __name__ == "__main__":  # pragma: no cover
    serve_stdio()
