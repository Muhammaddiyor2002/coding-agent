"""Runtime configuration for ShrekAgent loaded from environment / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_MAX_TOKENS = 8192

DEFAULT_BASH_ALLOWLIST: tuple[str, ...] = (
    "ls",
    "pwd",
    "cat",
    "head",
    "tail",
    "wc",
    "echo",
    "grep",
    "rg",
    "find",
    "tree",
    "file",
    "stat",
    "python",
    "python3",
    "pip",
    "uv",
    "pytest",
    "ruff",
    "mypy",
    "node",
    "npm",
    "pnpm",
    "yarn",
    "git status",
    "git diff",
    "git log",
    "git branch",
    "git show",
)


@dataclass(slots=True)
class Config:
    """User-facing configuration for the agent runtime."""

    api_key: str | None
    model: str
    max_tokens: int
    workspace: Path
    bash_allowlist: tuple[str, ...] = field(default_factory=lambda: DEFAULT_BASH_ALLOWLIST)
    bash_allow_all: bool = False

    @classmethod
    def from_env(cls, *, workspace: Path | None = None) -> Config:
        """Build a Config from process environment, loading ``.env`` if present."""
        load_dotenv(override=False)

        raw_workspace = workspace or Path(os.getenv("SHREK_WORKSPACE", ".")).resolve()
        raw_allowlist = os.getenv("SHREK_BASH_ALLOWLIST", "").strip()

        if raw_allowlist == "*":
            allow_all = True
            allowlist = DEFAULT_BASH_ALLOWLIST
        elif raw_allowlist:
            allow_all = False
            extra = tuple(item.strip() for item in raw_allowlist.split(",") if item.strip())
            allowlist = DEFAULT_BASH_ALLOWLIST + extra
        else:
            allow_all = False
            allowlist = DEFAULT_BASH_ALLOWLIST

        max_tokens_raw = os.getenv("SHREK_MAX_TOKENS", "").strip()
        try:
            max_tokens = int(max_tokens_raw) if max_tokens_raw else DEFAULT_MAX_TOKENS
        except ValueError:
            max_tokens = DEFAULT_MAX_TOKENS

        return cls(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model=os.getenv("SHREK_MODEL", DEFAULT_MODEL),
            max_tokens=max_tokens,
            workspace=raw_workspace,
            bash_allowlist=allowlist,
            bash_allow_all=allow_all,
        )
