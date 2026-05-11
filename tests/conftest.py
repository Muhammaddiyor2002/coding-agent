"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from shrek_agent.config import Config
from shrek_agent.tools.base import ToolContext


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """An isolated workspace directory for tool tests."""
    return tmp_path


@pytest.fixture()
def config(workspace: Path) -> Config:
    return Config(
        api_key="test-key",
        model="claude-sonnet-4-5",
        max_tokens=1024,
        workspace=workspace,
    )


@pytest.fixture()
def ctx(config: Config) -> ToolContext:
    return ToolContext(config=config)


@pytest.fixture()
def sample_tree(workspace: Path) -> Iterator[Path]:
    """Populate the workspace with a small example tree of files."""
    (workspace / "hello.py").write_text("print('hello')\n", encoding="utf-8")
    (workspace / "README.md").write_text("# demo\n\nsome text\n", encoding="utf-8")
    sub = workspace / "pkg"
    sub.mkdir()
    (sub / "__init__.py").write_text("", encoding="utf-8")
    (sub / "util.py").write_text(
        "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n",
        encoding="utf-8",
    )
    (workspace / ".git").mkdir()
    (workspace / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    yield workspace
