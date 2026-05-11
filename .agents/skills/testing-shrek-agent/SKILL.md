---
name: testing-shrek-agent
description: Runtime-test the ShrekAgent CLI end-to-end. Use when verifying any change to the `shrek` CLI, the agent loop, the tool registry, REPL slash-commands, or bash safety.
---

# Testing ShrekAgent (the `shrek` CLI)

## Devin Secrets Needed

- `ANTHROPIC_API_KEY` — **only** needed for a live Claude tool-use
  round-trip. Every other check (pytest suite, CLI smoke,
  REPL slash-commands) can be done without it.

## Quick setup

The repo has a `.venv` next to the source. Activate it before running
anything:

```bash
cd /home/ubuntu/repos/coding-agent
source .venv/bin/activate
```

If the venv is missing (fresh box), the environment blueprint will
rebuild it via `uv venv` + `uv pip install -e ".[dev]"`. You can also
do it manually with the same commands.

## What to test, in priority order

1. **`pytest -v`** — primary signal. Covers:
   - `tests/test_agent.py::test_tool_use_round_trip` — full agent loop
     via a `FakeClient` (offline). If you only have shell access this
     is the cheapest proof the tool dispatch still works.
   - `tests/test_agent.py::test_iteration_limit_keeps_conversation_valid`
     — regression for the Devin-Review fix that appends a synthetic
     assistant message after `MAX_TOOL_ITERATIONS`.
   - `tests/test_run_bash.py::test_dangerous_whitespace_bypass_blocked`
     and `…::test_dangerous_check_still_runs_when_allow_all` —
     regressions for the whitespace-bypass fix in the
     dangerous-command filter.

2. **CLI smoke** (no key needed):
   - `shrek --version` → exactly `shrek-agent 0.1.0`
   - `shrek --help` → must include `--workspace`, `--model`,
     `--version` and a `tools` subcommand row.
   - `shrek tools` → must list exactly 6 tools: `read_file`,
     `list_files`, `search_files`, `edit_file`, `write_file`,
     `run_bash`.
   - `ANTHROPIC_API_KEY= shrek` → red `ANTHROPIC_API_KEY is not set.`
     and process exits before the REPL banner.

3. **REPL slash-commands** (no key needed, see trick below):
   Anthropic's SDK only checks that the API key is **non-empty** at
   client construction; it doesn't validate it. Every `/...` branch in
   `shrek_agent/cli.py:_handle_slash` returns before any network call.
   So you can exercise all slash-commands offline with:

   ```bash
   mkdir -p /tmp/shrek-test
   ANTHROPIC_API_KEY=sk-fake-for-slash-only \
       shrek -w /tmp/shrek-test
   ```

   Then inside the REPL:
   - `/help`, `/tools`, `/cwd`, `/history`, `/reset`, `/exit` —
     pure-local, must match the strings in `_handle_slash`.
   - `/save <path>` then `/load <path>` — must round-trip and actually
     write/read the file on disk. Verify with `ls -la` after `/exit`.

   **Do NOT type a non-`/` line** into the REPL with a fake key — that
   path hits Anthropic and will surface a 401.

4. **Live Claude tool-use round-trip** (needs a real key):
   Only worth running when the change actually touches the agent loop
   / tool dispatch. If the user declines to provide a key, mark this
   as `untested` and rely on (1) for offline coverage. Don't keep
   asking for the key once they've said skip.

## Running in a recording

Konsole is the only GUI terminal on the box (`which konsole`):

```bash
DISPLAY=:0 konsole --workdir /home/ubuntu/repos/coding-agent \
    --geometry 1024x720+0+0 -e bash --noprofile --norc &
sleep 2
DISPLAY=:0 wmctrl -a "Konsole"
DISPLAY=:0 wmctrl -r :ACTIVE: -b add,maximized_vert,maximized_horz
```

When `shrek` is run from a konsole that inherited a parent shell with
`.venv` active, the venv stays active in the konsole — no extra
`source` needed inside the recording.

## Common gotchas

- **Anthropic 400 on iteration limit** (already fixed): if you ever
  see a 400 about message alternation after a long tool-call loop,
  check that `shrek_agent/agent.py` still appends the synthetic
  assistant message at the end of `_run_tool_loop` — if someone
  reverted that, `test_iteration_limit_keeps_conversation_valid` will
  fail.
- **Dangerous-command bypass via whitespace** (already fixed): the
  filter in `shrek_agent/tools/run_bash.py:_reject_dangerous` collapses
  whitespace before substring matching. If `rm  -rf` (double space) is
  ever accepted again, that normalization was removed.
- **`shrek tools` count mismatch**: if the count is not 6, either a
  tool was added without updating the test, or a tool was lost from
  `shrek_agent/tools/__init__.py:BUILTIN_TOOLS`.
- **REPL hangs on launch with placeholder key**: it shouldn't —
  construction is offline. If it does, something in `Agent.__init__`
  started calling the API eagerly; check recent changes there.

## CI

`.github/workflows/ci.yml` runs three jobs: `lint (ruff)`,
`typecheck (mypy)`, and `pytest` on Python 3.10 / 3.11 / 3.12. If any
of these go red, fix locally with `ruff check . && mypy shrek_agent &&
pytest` before re-running the runtime tests above.
