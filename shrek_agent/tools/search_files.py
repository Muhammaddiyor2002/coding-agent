"""Grep-like recursive search across the workspace."""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, Field

from shrek_agent.tools.base import Tool, ToolContext, ToolError
from shrek_agent.tools.list_files import IGNORED_DIRS

DEFAULT_MAX_MATCHES = 200
MAX_FILE_BYTES = 1_000_000


class SearchFilesInput(BaseModel):
    pattern: str = Field(description="Regular expression to search for (Python `re` syntax).")
    path: str | None = Field(
        default=None,
        description="Optional subdirectory to limit the search to. Defaults to workspace root.",
    )
    include: str | None = Field(
        default=None,
        description="Optional glob (e.g. '*.py') restricting which files are searched.",
    )
    case_insensitive: bool = Field(
        default=False,
        description="Match without regard to case.",
    )
    max_matches: int = Field(
        default=DEFAULT_MAX_MATCHES,
        description="Hard cap on the number of returned match lines.",
        ge=1,
        le=2000,
    )


class SearchFilesTool(Tool):
    name = "search_files"
    description = (
        "Search the workspace for a regex pattern. "
        "Returns `file:line:matched_text` lines, similar to `grep -rn`. "
        "Skips common ignore directories and binary/very large files."
    )
    InputModel = SearchFilesInput

    def run(self, args: BaseModel, ctx: ToolContext) -> str:
        assert isinstance(args, SearchFilesInput)
        try:
            flags = re.IGNORECASE if args.case_insensitive else 0
            regex = re.compile(args.pattern, flags)
        except re.error as exc:
            raise ToolError(f"invalid regex: {exc}") from exc

        base = ctx.resolve(args.path) if args.path else ctx.workspace.resolve()
        if not base.exists():
            raise ToolError(f"path not found: {args.path or '.'}")

        include_glob = args.include
        results: list[str] = []
        truncated = False

        for file_path in _iter_files(base):
            if include_glob and not file_path.match(include_glob):
                continue
            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            try:
                with file_path.open("r", encoding="utf-8", errors="strict") as fh:
                    for lineno, line in enumerate(fh, start=1):
                        if regex.search(line):
                            rel = os.path.relpath(file_path, ctx.workspace)
                            results.append(f"{rel}:{lineno}:{line.rstrip()}")
                            if len(results) >= args.max_matches:
                                truncated = True
                                break
            except (UnicodeDecodeError, OSError):
                continue
            if truncated:
                break

        if not results:
            return "(no matches)"

        out = "\n".join(results)
        if truncated:
            out += f"\n… truncated to {args.max_matches} matches"
        return out

    def call_summary(self, args: BaseModel) -> str:
        assert isinstance(args, SearchFilesInput)
        scope = args.path or "."
        flags = "i" if args.case_insensitive else ""
        glob = f" include={args.include}" if args.include else ""
        return f"{args.pattern!r} in {scope}{glob}  [{flags}]"


def _iter_files(base: Path) -> Iterator[Path]:
    if base.is_file():
        yield base
        return
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        root_p = Path(root)
        for f in files:
            yield root_p / f
