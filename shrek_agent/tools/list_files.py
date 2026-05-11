"""List files and directories under a workspace path."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field

from shrek_agent.tools.base import Tool, ToolContext, ToolError

DEFAULT_MAX_ENTRIES = 500
IGNORED_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".tox",
        ".idea",
        ".vscode",
    }
)


class ListFilesInput(BaseModel):
    path: str | None = Field(
        default=None,
        description="Relative path to list. Defaults to the workspace root.",
    )
    recursive: bool = Field(
        default=True,
        description="Walk subdirectories. Common build/cache directories are skipped.",
    )
    max_entries: int = Field(
        default=DEFAULT_MAX_ENTRIES,
        description="Hard cap on the number of returned entries.",
        ge=1,
        le=5000,
    )


class ListFilesTool(Tool):
    name = "list_files"
    description = (
        "List files and directories at a workspace path. "
        "Recursive by default; auto-skips common ignore dirs (.git, node_modules, .venv, …). "
        "Directories end with `/`. Output is capped at `max_entries` entries."
    )
    InputModel = ListFilesInput

    def run(self, args: BaseModel, ctx: ToolContext) -> str:
        assert isinstance(args, ListFilesInput)
        base = ctx.resolve(args.path) if args.path else ctx.workspace.resolve()

        if not base.exists():
            raise ToolError(f"path not found: {args.path or '.'}")

        if base.is_file():
            return ctx.relpath(base)

        entries = sorted(_walk(base, recursive=args.recursive))
        truncated = False
        if len(entries) > args.max_entries:
            entries = entries[: args.max_entries]
            truncated = True

        rels = [_format(base, p) for p in entries]
        out = "\n".join(rels) if rels else "(empty directory)"
        if truncated:
            out += f"\n… truncated to {args.max_entries} entries"
        return out

    def call_summary(self, args: BaseModel) -> str:
        assert isinstance(args, ListFilesInput)
        kind = "recursive" if args.recursive else "shallow"
        return f"{args.path or '.'}  ({kind})"


def _walk(base: Path, *, recursive: bool) -> list[Path]:
    out: list[Path] = []
    if not recursive:
        for child in base.iterdir():
            out.append(child)
        return out

    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        root_p = Path(root)
        for d in dirs:
            out.append(root_p / d)
        for f in files:
            out.append(root_p / f)
    return out


def _format(base: Path, p: Path) -> str:
    rel = os.path.relpath(p, base)
    if p.is_dir():
        return f"{rel}/"
    return rel
