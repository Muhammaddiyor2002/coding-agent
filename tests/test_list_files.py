"""Tests for the list_files tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from shrek_agent.tools.base import ToolError
from shrek_agent.tools.list_files import ListFilesInput, ListFilesTool


def test_lists_workspace(ctx, sample_tree: Path) -> None:
    tool = ListFilesTool()
    out = tool.run(ListFilesInput(), ctx)
    lines = set(out.splitlines())
    assert "hello.py" in lines
    assert "README.md" in lines
    assert "pkg/" in lines
    assert "pkg/util.py" in lines
    # ignored
    assert all(".git" not in line for line in lines)


def test_shallow_listing(ctx, sample_tree: Path) -> None:
    tool = ListFilesTool()
    out = tool.run(ListFilesInput(recursive=False), ctx)
    lines = set(out.splitlines())
    assert "pkg/" in lines
    assert "pkg/util.py" not in lines


def test_missing_path(ctx) -> None:
    tool = ListFilesTool()
    with pytest.raises(ToolError, match="not found"):
        tool.run(ListFilesInput(path="nowhere"), ctx)


def test_max_entries_truncates(ctx, workspace: Path) -> None:
    for i in range(10):
        (workspace / f"f{i}.txt").write_text("x", encoding="utf-8")
    tool = ListFilesTool()
    out = tool.run(ListFilesInput(max_entries=3), ctx)
    assert "truncated" in out
