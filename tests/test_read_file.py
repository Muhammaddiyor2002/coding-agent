"""Tests for the read_file tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from shrek_agent.tools.base import ToolError
from shrek_agent.tools.read_file import ReadFileInput, ReadFileTool


def test_reads_existing_file(ctx, sample_tree: Path) -> None:
    tool = ReadFileTool()
    out = tool.run(ReadFileInput(path="hello.py"), ctx)
    assert out == "print('hello')\n"


def test_missing_file(ctx, workspace: Path) -> None:
    tool = ReadFileTool()
    with pytest.raises(ToolError, match="file not found"):
        tool.run(ReadFileInput(path="missing.txt"), ctx)


def test_directory_rejected(ctx, sample_tree: Path) -> None:
    tool = ReadFileTool()
    with pytest.raises(ToolError, match="directory"):
        tool.run(ReadFileInput(path="pkg"), ctx)


def test_path_escape_blocked(ctx, workspace: Path, tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    tool = ReadFileTool()
    with pytest.raises(ToolError, match="outside the workspace"):
        tool.run(ReadFileInput(path=str(outside)), ctx)


def test_line_slicing(ctx, workspace: Path) -> None:
    (workspace / "lines.txt").write_text("a\nb\nc\nd\ne\n", encoding="utf-8")
    tool = ReadFileTool()
    out = tool.run(ReadFileInput(path="lines.txt", start_line=2, end_line=4), ctx)
    assert out == "b\nc\nd\n"


def test_invalid_slice(ctx, workspace: Path) -> None:
    (workspace / "lines.txt").write_text("a\nb\nc\n", encoding="utf-8")
    tool = ReadFileTool()
    with pytest.raises(ToolError, match="start_line"):
        tool.run(ReadFileInput(path="lines.txt", start_line=5, end_line=2), ctx)
