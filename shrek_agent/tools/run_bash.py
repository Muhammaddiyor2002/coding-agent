"""Run a shell command under a strict allow-list."""

from __future__ import annotations

import shlex
import subprocess

from pydantic import BaseModel, Field

from shrek_agent.tools.base import Tool, ToolContext, ToolError

DEFAULT_TIMEOUT = 60
MAX_TIMEOUT = 600
MAX_OUTPUT_BYTES = 50_000

DANGEROUS_SNIPPETS: tuple[str, ...] = (
    "rm -rf",
    "rm -fr",
    ":(){",
    "mkfs",
    "dd if=",
    "shutdown",
    "reboot",
    "curl ",
    "wget ",
    "ssh ",
    "scp ",
    "sudo ",
    "git push",
    "git reset --hard",
    "git clean -fd",
    "git checkout --",
)


class RunBashInput(BaseModel):
    command: str = Field(
        description=(
            "Shell command to execute. Must start with an allow-listed prefix "
            "(see `SHREK_BASH_ALLOWLIST`). Pipes/redirects are allowed if every "
            "command in the pipeline is allow-listed."
        )
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        description="Wall-clock timeout in seconds.",
        ge=1,
        le=MAX_TIMEOUT,
    )


class RunBashTool(Tool):
    name = "run_bash"
    description = (
        "Run a shell command in the workspace under a strict allow-list of safe prefixes "
        "(ls, cat, head, tail, grep, rg, python, pytest, ruff, …). "
        "Returns combined stdout+stderr. Use this to inspect files, run tests, or "
        "list git status — never to push, install untrusted code, or modify the system."
    )
    InputModel = RunBashInput

    def run(self, args: BaseModel, ctx: ToolContext) -> str:
        assert isinstance(args, RunBashInput)
        command = args.command.strip()
        if not command:
            raise ToolError("command must not be empty")

        _reject_dangerous(command)
        if not ctx.config.bash_allow_all:
            _enforce_allowlist(command, ctx.config.bash_allowlist)

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=ctx.workspace,
                capture_output=True,
                text=True,
                timeout=args.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolError(f"command timed out after {args.timeout}s") from exc
        except OSError as exc:
            raise ToolError(f"failed to spawn command: {exc}") from exc

        out = (proc.stdout or "") + (proc.stderr or "")
        if len(out) > MAX_OUTPUT_BYTES:
            out = out[:MAX_OUTPUT_BYTES] + f"\n… output truncated at {MAX_OUTPUT_BYTES} bytes"
        return f"$ {command}\n[exit {proc.returncode}]\n{out}".rstrip() + "\n"

    def call_summary(self, args: BaseModel) -> str:
        assert isinstance(args, RunBashInput)
        snippet = args.command
        if len(snippet) > 60:
            snippet = snippet[:57] + "…"
        return snippet


def _reject_dangerous(command: str) -> None:
    # Collapse runs of whitespace so that e.g. `rm  -rf` (double space) still
    # matches the `rm -rf` snippet. This matters when bash_allow_all is set,
    # because the allow-list gate is skipped and this check is the last guard.
    lower = " " + " ".join(command.lower().split()) + " "
    for needle in DANGEROUS_SNIPPETS:
        if needle in lower:
            raise ToolError(f"refusing to run dangerous command (matched: {needle!r})")


def _enforce_allowlist(command: str, allowlist: tuple[str, ...]) -> None:
    """Reject the command unless every pipeline segment starts with an allowed prefix."""
    segments = _split_pipeline(command)
    for segment in segments:
        if not _segment_allowed(segment, allowlist):
            raise ToolError(
                f"command {segment!r} is not allow-listed — "
                "set SHREK_BASH_ALLOWLIST to extend allowed prefixes"
            )


def _split_pipeline(command: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    in_single = False
    in_double = False
    i = 0
    while i < len(command):
        ch = command[i]
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        if not in_single and not in_double and command[i : i + 2] in {"&&", "||"}:
            parts.append("".join(buf).strip())
            buf = []
            i += 2
            continue
        if not in_single and not in_double and ch in {"|", ";"}:
            parts.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return [p for p in parts if p]


def _segment_allowed(segment: str, allowlist: tuple[str, ...]) -> bool:
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return False
    if not tokens:
        return False
    for prefix in allowlist:
        prefix_tokens = prefix.split()
        if tokens[: len(prefix_tokens)] == prefix_tokens:
            return True
    return False
