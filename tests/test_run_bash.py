"""Tests for the run_bash tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from shrek_agent.tools.base import ToolError
from shrek_agent.tools.run_bash import RunBashInput, RunBashTool


def test_simple_command(ctx, sample_tree: Path) -> None:
    tool = RunBashTool()
    out = tool.run(RunBashInput(command="ls"), ctx)
    assert "hello.py" in out
    assert "[exit 0]" in out


def test_pipeline_allowed(ctx, sample_tree: Path) -> None:
    tool = RunBashTool()
    out = tool.run(RunBashInput(command="ls | grep py"), ctx)
    assert "hello.py" in out


def test_blocked_command(ctx, sample_tree: Path) -> None:
    tool = RunBashTool()
    with pytest.raises(ToolError, match="not allow-listed"):
        tool.run(RunBashInput(command="apt install x"), ctx)


def test_dangerous_rejected(ctx, sample_tree: Path) -> None:
    tool = RunBashTool()
    with pytest.raises(ToolError, match="dangerous"):
        tool.run(RunBashInput(command="rm -rf /"), ctx)


def test_dangerous_in_pipeline_rejected(ctx, sample_tree: Path) -> None:
    tool = RunBashTool()
    with pytest.raises(ToolError, match="dangerous"):
        tool.run(RunBashInput(command="ls | sudo rm something"), ctx)


def test_empty_command(ctx) -> None:
    tool = RunBashTool()
    with pytest.raises(ToolError, match="empty"):
        tool.run(RunBashInput(command="   "), ctx)
