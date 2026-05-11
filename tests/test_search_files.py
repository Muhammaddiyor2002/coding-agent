"""Tests for the search_files tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from shrek_agent.tools.base import ToolError
from shrek_agent.tools.search_files import SearchFilesInput, SearchFilesTool


def test_finds_match(ctx, sample_tree: Path) -> None:
    tool = SearchFilesTool()
    out = tool.run(SearchFilesInput(pattern=r"def add"), ctx)
    assert "pkg/util.py" in out
    assert "def add" in out


def test_case_insensitive(ctx, sample_tree: Path) -> None:
    tool = SearchFilesTool()
    out = tool.run(SearchFilesInput(pattern="DEMO", case_insensitive=True), ctx)
    assert "README.md" in out


def test_include_glob(ctx, sample_tree: Path) -> None:
    tool = SearchFilesTool()
    out = tool.run(SearchFilesInput(pattern=r"def", include="*.py"), ctx)
    assert "pkg/util.py" in out
    assert "README.md" not in out


def test_no_match(ctx, sample_tree: Path) -> None:
    tool = SearchFilesTool()
    out = tool.run(SearchFilesInput(pattern=r"xyznotpresent"), ctx)
    assert out == "(no matches)"


def test_invalid_regex(ctx, sample_tree: Path) -> None:
    tool = SearchFilesTool()
    with pytest.raises(ToolError, match="invalid regex"):
        tool.run(SearchFilesInput(pattern=r"["), ctx)
