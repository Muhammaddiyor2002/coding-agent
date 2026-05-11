"""Read a file from the workspace."""

from __future__ import annotations

from pydantic import BaseModel, Field

from shrek_agent.tools.base import Tool, ToolContext, ToolError

MAX_READ_BYTES = 200_000


class ReadFileInput(BaseModel):
    path: str = Field(description="Relative path to a file inside the workspace.")
    start_line: int | None = Field(
        default=None,
        description="Optional 1-indexed first line to include. Omit to read from the top.",
    )
    end_line: int | None = Field(
        default=None,
        description="Optional 1-indexed last line to include (inclusive). Omit to read to EOF.",
    )


class ReadFileTool(Tool):
    name = "read_file"
    description = (
        "Read the contents of a file in the workspace. "
        "Supports optional 1-indexed line slicing via `start_line` / `end_line`. "
        "Returns plain text; use `list_files` for directories."
    )
    InputModel = ReadFileInput

    def run(self, args: BaseModel, ctx: ToolContext) -> str:
        assert isinstance(args, ReadFileInput)
        path = ctx.resolve(args.path)

        if not path.exists():
            raise ToolError(f"file not found: {args.path}")
        if path.is_dir():
            raise ToolError(f"{args.path} is a directory — use list_files instead")

        try:
            data = path.read_bytes()
        except OSError as exc:
            raise ToolError(f"failed to read {args.path}: {exc}") from exc

        if len(data) > MAX_READ_BYTES:
            raise ToolError(
                f"file too large ({len(data)} bytes > {MAX_READ_BYTES}); "
                "use start_line/end_line to read a slice"
            )

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ToolError(f"file is not valid UTF-8: {exc}") from exc

        if args.start_line is None and args.end_line is None:
            return text

        lines = text.splitlines(keepends=True)
        start = max(1, args.start_line or 1)
        end = args.end_line or len(lines)
        end = min(end, len(lines))
        if start > end:
            raise ToolError(f"start_line ({start}) > end_line ({end})")
        return "".join(lines[start - 1 : end])

    def call_summary(self, args: BaseModel) -> str:
        assert isinstance(args, ReadFileInput)
        slice_desc = ""
        if args.start_line is not None or args.end_line is not None:
            slice_desc = f"  [{args.start_line or 1}:{args.end_line or '$'}]"
        return f"{args.path}{slice_desc}"
