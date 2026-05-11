"""Tests for the edit_file tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from shrek_agent.tools.base import ToolError
from shrek_agent.tools.edit_file import EditFileInput, EditFileTool


def test_single_replacement(ctx, workspace: Path) -> None:
    (workspace / "f.txt").write_text("hello world\n", encoding="utf-8")
    tool = EditFileTool()
    msg = tool.run(EditFileInput(path="f.txt", old_str="world", new_str="shrek"), ctx)
    assert "Edited" in msg
    assert (workspace / "f.txt").read_text() == "hello shrek\n"


def test_no_match(ctx, workspace: Path) -> None:
    (workspace / "f.txt").write_text("hello\n", encoding="utf-8")
    tool = EditFileTool()
    with pytest.raises(ToolError, match="not found"):
        tool.run(EditFileInput(path="f.txt", old_str="missing", new_str="x"), ctx)


def test_ambiguous_match(ctx, workspace: Path) -> None:
    (workspace / "f.txt").write_text("foo foo\n", encoding="utf-8")
    tool = EditFileTool()
    with pytest.raises(ToolError, match="matches 2 times"):
        tool.run(EditFileInput(path="f.txt", old_str="foo", new_str="bar"), ctx)


def test_create_via_empty_old_str(ctx, workspace: Path) -> None:
    tool = EditFileTool()
    msg = tool.run(EditFileInput(path="new/file.txt", old_str="", new_str="content"), ctx)
    assert "Created" in msg
    assert (workspace / "new" / "file.txt").read_text() == "content"


def test_old_equals_new(ctx, workspace: Path) -> None:
    (workspace / "f.txt").write_text("foo\n", encoding="utf-8")
    tool = EditFileTool()
    with pytest.raises(ToolError, match="must differ"):
        tool.run(EditFileInput(path="f.txt", old_str="foo", new_str="foo"), ctx)


def test_refuse_to_wipe_existing(ctx, workspace: Path) -> None:
    (workspace / "f.txt").write_text("important", encoding="utf-8")
    tool = EditFileTool()
    with pytest.raises(ToolError, match="refusing to wipe"):
        tool.run(EditFileInput(path="f.txt", old_str="", new_str="x"), ctx)
