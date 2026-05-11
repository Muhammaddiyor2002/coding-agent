"""Typer-based CLI entry point for ShrekAgent."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from shrek_agent import __version__
from shrek_agent.agent import Agent
from shrek_agent.config import Config
from shrek_agent.console import banner, console, render_info

app = typer.Typer(
    help="ShrekAgent — Claude Code-style terminal coding agent.",
    no_args_is_help=False,
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    workspace: Annotated[
        Path | None,
        typer.Option(
            "--workspace",
            "-w",
            help="Directory the agent is allowed to read/edit. Defaults to current dir.",
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", "-m", help="Override the Claude model (env: SHREK_MODEL)."),
    ] = None,
    show_version: Annotated[
        bool,
        typer.Option("--version", "-V", help="Print version and exit.", is_eager=True),
    ] = False,
) -> None:
    """Run the interactive ShrekAgent REPL by default."""
    if show_version:
        console.print(f"shrek-agent {__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is not None:
        return

    config = Config.from_env(workspace=workspace)
    if model:
        config.model = model

    if not config.api_key:
        console.print(
            "[bold red]ANTHROPIC_API_KEY is not set.[/bold red]\n"
            "Get one at https://console.anthropic.com/settings/keys and either "
            "`export ANTHROPIC_API_KEY=...` or put it in a `.env` file."
        )
        raise typer.Exit(code=2)

    _run_repl(config)


@app.command("tools")
def tools_cmd() -> None:
    """List all built-in tools and exit."""
    from shrek_agent.tools import default_tools

    for tool in default_tools():
        first_line = tool.description.strip().splitlines()[0]
        console.print(f"[bold green]{tool.name}[/bold green]  [dim]— {first_line}[/dim]")


@app.command("mcp")
def mcp_cmd(
    workspace: Annotated[
        Path | None,
        typer.Option(
            "--workspace",
            "-w",
            help="Directory the MCP server is allowed to read/edit. Defaults to current dir.",
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
) -> None:
    """Run ShrekAgent as an MCP server over stdio.

    Other MCP clients (Claude Desktop, Cursor, Zed, …) can connect to this
    server to call the same six tools the agent uses internally. No
    ``ANTHROPIC_API_KEY`` is needed — the host LLM does its own model calls.
    """
    from shrek_agent.mcp_server import serve_stdio

    config = Config.from_env(workspace=workspace)
    # Visible only on stderr because the server owns stdout.
    sys.stderr.write(
        f"shrek-agent MCP server | workspace: {config.workspace}\n"
        "speaking JSON-RPC over stdio; press Ctrl-C to stop.\n"
    )
    sys.stderr.flush()
    try:
        serve_stdio(config=config)
    except KeyboardInterrupt:
        sys.stderr.write("shrek-agent MCP server: bye\n")
        sys.stderr.flush()


def _run_repl(config: Config) -> None:
    from anthropic import Anthropic  # imported lazily for fast --help / `tools` subcommand

    client = Anthropic(api_key=config.api_key)
    agent = Agent(config=config, client=client)

    console.print(banner())
    render_info(f"workspace: {config.workspace}")
    render_info(f"model:     {config.model}")

    history_path = config.workspace / ".shrek" / "input_history"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    session: PromptSession[str] = PromptSession(history=FileHistory(str(history_path)))

    while True:
        try:
            user_input = session.prompt("You ❯ ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]goodbye 👋[/dim]")
            return

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.startswith("/"):
            if _handle_slash(user_input, agent):
                return
            continue

        try:
            agent.send(user_input)
        except KeyboardInterrupt:
            render_info("⚠ interrupted")
        except Exception as exc:
            console.print(f"[bold red]error:[/bold red] {exc}")


def _handle_slash(command: str, agent: Agent) -> bool:
    """Handle ``/...`` slash-commands. Return ``True`` if the REPL should exit."""
    parts = command.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in {"/exit", "/quit", "/q"}:
        console.print("[dim]bye 👋[/dim]")
        return True

    if cmd in {"/help", "/?"}:
        console.print(
            "[bold]Slash commands[/bold]\n"
            "  /help            show this help\n"
            "  /tools           list registered tools\n"
            "  /history         print the current conversation length\n"
            "  /reset           clear the conversation\n"
            "  /save <path>     save conversation history to a JSON file\n"
            "  /load <path>     load conversation history from a JSON file\n"
            "  /cwd             print the workspace path\n"
            "  /exit            quit"
        )
        return False

    if cmd == "/tools":
        for tool in agent.tools:
            first_line = tool.description.strip().splitlines()[0]
            console.print(f"  [bold green]{tool.name}[/bold green]  [dim]— {first_line}[/dim]")
        return False

    if cmd == "/history":
        n = len(agent.conversation)
        render_info(f"conversation has {n} message(s)")
        return False

    if cmd == "/reset":
        agent.reset()
        render_info("conversation cleared")
        return False

    if cmd == "/cwd":
        render_info(str(agent.config.workspace))
        return False

    if cmd == "/save":
        if not arg:
            console.print("[red]usage:[/red] /save <path>")
            return False
        path = Path(arg).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(agent.history_json(), encoding="utf-8")
        render_info(f"saved {len(agent.conversation)} message(s) → {path}")
        return False

    if cmd == "/load":
        if not arg:
            console.print("[red]usage:[/red] /load <path>")
            return False
        path = Path(arg).expanduser()
        if not path.exists():
            console.print(f"[red]not found:[/red] {path}")
            return False
        try:
            agent.load_history(path.read_text(encoding="utf-8"))
        except Exception as exc:
            console.print(f"[red]failed to load:[/red] {exc}")
            return False
        render_info(f"loaded {len(agent.conversation)} message(s) ← {path}")
        return False

    console.print(f"[red]unknown command:[/red] {cmd}  (try /help)")
    return False


mcp_app = typer.Typer(
    help="ShrekAgent MCP server (stdio). Exposes the six built-in tools to any MCP client.",
    no_args_is_help=False,
    add_completion=False,
)


@mcp_app.callback(invoke_without_command=True)
def mcp_main(
    workspace: Annotated[
        Path | None,
        typer.Option(
            "--workspace",
            "-w",
            help="Directory the MCP server is allowed to read/edit. Defaults to current dir.",
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
) -> None:
    """Entry point for the ``shrek-mcp`` console script."""
    mcp_cmd(workspace=workspace)


if __name__ == "__main__":  # pragma: no cover
    app()
    sys.exit(0)
