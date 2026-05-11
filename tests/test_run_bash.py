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


def test_dangerous_whitespace_bypass_blocked(ctx, sample_tree: Path) -> None:
    """Extra whitespace inside a dangerous snippet must not slip past the filter.

    The check normalizes consecutive spaces so that `rm  -rf /` (double space)
    is rejected with the same `rm -rf` snippet match. Without normalization
    this is the last guard when bash_allow_all is enabled.
    """
    tool = RunBashTool()
    with pytest.raises(ToolError, match="dangerous"):
        tool.run(RunBashInput(command="rm  -rf /tmp/whatever"), ctx)
    with pytest.raises(ToolError, match="dangerous"):
        tool.run(RunBashInput(command="sudo\t  apt install evil"), ctx)


def test_dangerous_check_still_runs_when_allow_all(ctx, sample_tree: Path) -> None:
    """Even with SHREK_BASH_ALLOWLIST=* the dangerous-snippet filter still fires."""
    ctx.config.bash_allow_all = True
    tool = RunBashTool()
    with pytest.raises(ToolError, match="dangerous"):
        tool.run(RunBashInput(command="rm  -rf /"), ctx)
