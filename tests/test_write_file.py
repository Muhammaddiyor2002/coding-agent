"""Tests for the write_file tool."""

from __future__ import annotations

from pathlib import Path

from shrek_agent.tools.write_file import WriteFileInput, WriteFileTool


def test_create_new_file(ctx, workspace: Path) -> None:
    tool = WriteFileTool()
    msg = tool.run(WriteFileInput(path="a/b/c.txt", content="hello"), ctx)
    assert (workspace / "a" / "b" / "c.txt").read_text() == "hello"
    assert "Created" in msg


def test_overwrite_existing(ctx, workspace: Path) -> None:
    (workspace / "f.txt").write_text("old", encoding="utf-8")
    tool = WriteFileTool()
    msg = tool.run(WriteFileInput(path="f.txt", content="new"), ctx)
    assert (workspace / "f.txt").read_text() == "new"
    assert "Overwrote" in msg
