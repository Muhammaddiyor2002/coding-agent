"""Create a new file or overwrite an existing one."""

from __future__ import annotations

from pydantic import BaseModel, Field

from shrek_agent.tools.base import Tool, ToolContext


class WriteFileInput(BaseModel):
    path: str = Field(description="Relative path to the file inside the workspace.")
    content: str = Field(description="Full UTF-8 content to write to the file.")


class WriteFileTool(Tool):
    name = "write_file"
    description = (
        "Create a new file or fully overwrite an existing one with the given content. "
        "Parent directories are created automatically. "
        "Prefer `edit_file` for targeted modifications inside an existing file."
    )
    InputModel = WriteFileInput

    def run(self, args: BaseModel, ctx: ToolContext) -> str:
        assert isinstance(args, WriteFileInput)
        path = ctx.resolve(args.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        existed = path.exists()
        path.write_text(args.content, encoding="utf-8")
        verb = "Overwrote" if existed else "Created"
        return f"{verb} {ctx.relpath(path)} ({len(args.content)} chars)."

    def call_summary(self, args: BaseModel) -> str:
        assert isinstance(args, WriteFileInput)
        return f"{args.path}  ({len(args.content)} chars)"
