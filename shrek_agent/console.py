"""Shared Rich console + helpers for pretty terminal output."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

console = Console()


def banner() -> Panel:
    """Return the welcome banner shown at startup."""
    body = Text.from_markup(
        "[bold green]ShrekAgent[/bold green] — Claude-powered coding agent\n"
        "[dim]Type [bold]/help[/bold] for commands. Press [bold]Ctrl-D[/bold] or "
        "type [bold]/exit[/bold] to quit.[/dim]"
    )
    return Panel(body, border_style="green", padding=(1, 2))


def render_assistant(text: str) -> None:
    """Render assistant text using Markdown rendering."""
    if not text.strip():
        return
    console.print()
    console.print(Markdown(text))


def render_user_prefix() -> Text:
    return Text("You ❯ ", style="bold blue")


def render_tool_call(name: str, summary: str) -> None:
    console.print(
        Text("• ", style="green")
        + Text(f"{name}", style="bold green")
        + Text(f"  {summary}", style="dim")
    )


def render_tool_error(name: str, error: str) -> None:
    console.print(
        Text("✗ ", style="red")
        + Text(f"{name}", style="bold red")
        + Text(f"  {error}", style="dim red")
    )


def render_info(message: str) -> None:
    console.print(Text(f"  {message}", style="dim"))
