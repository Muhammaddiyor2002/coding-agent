"""Make a targeted ``old_str`` → ``new_str`` edit inside a single file."""

from __future__ import annotations

from pydantic import BaseModel, Field

from shrek_agent.tools.base import Tool, ToolContext, ToolError


class EditFileInput(BaseModel):
    path: str = Field(description="Relative path to the file inside the workspace.")
    old_str: str = Field(
        description=(
            "Exact text to search for. Must match exactly once in the file. "
            "Pass an empty string together with a non-existent path to create a new file."
        )
    )
    new_str: str = Field(description="Text to replace `old_str` with.")


class EditFileTool(Tool):
    name = "edit_file"
    description = (
        "Replace an exact occurrence of `old_str` with `new_str` in a file. "
        "`old_str` must appear exactly once. If the file does not exist and `old_str` is empty, "
        "the file is created with `new_str` as its content. Use `write_file` for full overwrites."
    )
    InputModel = EditFileInput

    def run(self, args: BaseModel, ctx: ToolContext) -> str:
        assert isinstance(args, EditFileInput)
        if args.old_str == args.new_str:
            raise ToolError("old_str and new_str must differ")

        path = ctx.resolve(args.path)

        if not path.exists():
            if args.old_str != "":
                raise ToolError(f"file not found: {args.path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args.new_str, encoding="utf-8")
            return f"Created {ctx.relpath(path)} ({len(args.new_str)} chars)."

        if path.is_dir():
            raise ToolError(f"{args.path} is a directory")

        content = path.read_text(encoding="utf-8")

        if args.old_str == "":
            raise ToolError(
                f"refusing to wipe {args.path}: pass a non-empty old_str or use write_file"
            )

        count = content.count(args.old_str)
        if count == 0:
            raise ToolError("old_str not found in the file")
        if count > 1:
            raise ToolError(
                f"old_str matches {count} times — make it more specific so the match is unique"
            )

        new_content = content.replace(args.old_str, args.new_str, 1)
        path.write_text(new_content, encoding="utf-8")
        return f"Edited {ctx.relpath(path)}: replaced 1 occurrence."

    def call_summary(self, args: BaseModel) -> str:
        assert isinstance(args, EditFileInput)
        snippet = args.old_str.replace("\n", "⏎")
        if len(snippet) > 40:
            snippet = snippet[:37] + "…"
        return f"{args.path}  ({snippet!r})"
