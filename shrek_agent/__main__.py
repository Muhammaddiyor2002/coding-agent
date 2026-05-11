"""Allow ``python -m shrek_agent`` as an alternative entry point."""

from __future__ import annotations

from shrek_agent.cli import app

if __name__ == "__main__":
    app()
