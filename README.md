# ShrekAgent — Claude Code-style coding agent in Python

[![CI](https://github.com/Muhammaddiyor2002/coding-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Muhammaddiyor2002/coding-agent/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A small, focused, hackable terminal coding agent inspired by
[Anthropic's Claude Code](https://docs.claude.com/en/docs/claude-code) and the
[Amp "How to build an agent"](https://ampcode.com/how-to-build-an-agent) tutorial.
Built live on a [Practical Coders](https://www.youtube.com/watch?v=0aFH6jRe2PM) stream and
polished here into a production-quality Python package.

> An LLM, a loop, and enough tokens — that's all an agent really is.

## Highlights

- **Six built-in tools** — `read_file`, `write_file`, `edit_file`, `list_files`,
  `search_files` (regex grep), `run_bash` (with a strict allow-list).
- **Pretty terminal UI** — Rich-powered Markdown rendering of Claude's replies,
  colored tool-call traces, prompt-toolkit input with persistent history.
- **Slash commands** — `/help`, `/tools`, `/reset`, `/history`, `/save`, `/load`,
  `/cwd`, `/exit`.
- **Safe by default** — every tool path is validated against the workspace root and
  cannot escape via `..`; `run_bash` rejects dangerous patterns (`rm -rf`,
  `sudo`, `git push`, …) and only runs commands whose prefix is on an allow-list.
- **Configurable** — read `ANTHROPIC_API_KEY`, model, max tokens, workspace, and
  the bash allow-list from environment variables or a local `.env`.
- **Fully tested + typed** — `pytest`, `ruff`, `mypy --strict` in CI across
  Python 3.10 / 3.11 / 3.12.

## Installation

```bash
git clone https://github.com/Muhammaddiyor2002/coding-agent.git
cd coding-agent
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Or, with [uv](https://docs.astral.sh/uv/):

```bash
uv venv && source .venv/bin/activate
uv pip install -e .
```

## Quick start

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
shrek
```

```
╭───────────────────────────────────────────────────────────╮
│ ShrekAgent — Claude-powered coding agent                  │
│ Type /help for commands. Press Ctrl-D or type /exit to    │
│ quit.                                                     │
╰───────────────────────────────────────────────────────────╯
  workspace: /home/me/proj
  model:     claude-sonnet-4-5
You ❯ list the python files in this project
• list_files .  (recursive)
• read_file pyproject.toml

Here's the layout:

  - `shrek_agent/` — the agent package
  - `tests/` — pytest suite
  …

You ❯ write a tiny snake game in snake.py
• write_file snake.py  (1842 chars)

Done — run `python snake.py` to play.

You ❯ /exit
```

You can also run it as a module:

```bash
python -m shrek_agent
```

## Configuration

Every option has both an env-var and a `.env` form. Copy `.env.example` to `.env` and tweak:

| Variable               | Default              | Meaning                                                    |
| ---------------------- | -------------------- | ---------------------------------------------------------- |
| `ANTHROPIC_API_KEY`    | _(required)_         | Your Anthropic API key.                                    |
| `SHREK_MODEL`          | `claude-sonnet-4-5`  | Claude model to use.                                       |
| `SHREK_MAX_TOKENS`     | `8192`               | Max tokens per response.                                   |
| `SHREK_WORKSPACE`      | current directory    | Root directory the agent is allowed to touch.              |
| `SHREK_BASH_ALLOWLIST` | _(see `config.py`)_  | Comma-separated extra allowed shell prefixes, or `*`.      |

CLI flags (`--workspace`, `--model`, `--version`) override env values for a single run:

```bash
shrek --workspace ./my-project --model claude-opus-4-5
```

## Tools

| Tool           | Description                                                                                  |
| -------------- | -------------------------------------------------------------------------------------------- |
| `read_file`    | Read a file (optionally a `[start_line:end_line]` slice). Refuses dirs and oversized files.  |
| `list_files`   | List files & dirs at a path. Recursive by default, skips `.git`/`node_modules`/`.venv`/…     |
| `search_files` | Recursive regex search. Supports `include` glob, case-insensitive mode, and result caps.     |
| `edit_file`    | `old_str` → `new_str` replace. Requires a unique match. Empty `old_str` creates a new file.  |
| `write_file`   | Create or fully overwrite a file. Parent directories are created automatically.              |
| `run_bash`     | Run an allow-listed shell command (`ls`, `cat`, `pytest`, `ruff`, `git status`, …).          |

### Extending the agent

Adding a new tool is three steps:

1. Create `shrek_agent/tools/my_tool.py` with a `pydantic` input model and a `Tool` subclass.
2. Register it in `shrek_agent/tools/__init__.py` inside `default_tools()`.
3. (Optional) Add a `tests/test_my_tool.py` file mirroring the existing tests.

See `shrek_agent/tools/read_file.py` for a minimal example.

## How it works

The whole agent is a loop, roughly 100 lines:

1. Read a line of user input from the terminal.
2. Append it to the conversation and send to Claude (`/v1/messages`) along with
   the tool schema.
3. Claude responds with a mix of text blocks and `tool_use` blocks.
4. For each `tool_use`, look up the tool, validate the args with `pydantic`,
   execute it, and append a `tool_result` block.
5. If any tool ran, send the conversation back to Claude and go to step 3.
6. Otherwise, prompt the user again.

That's it. There is no hidden magic. The full implementation lives in
[`shrek_agent/agent.py`](shrek_agent/agent.py).

## Development

```bash
pip install -e ".[dev]"

# tests
pytest

# lint + format check
ruff check . && ruff format --check .

# type-check
mypy shrek_agent
```

CI runs the same three jobs on every push and PR. See
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## O'zbek tilida — qisqacha

Bu loyiha [Practical Coders](https://www.youtube.com/watch?v=0aFH6jRe2PM) kanalining
"0 dan Claude Code-ga o'xshash dasturlash agentini yozamiz" videosi asosida qurilgan,
production-tayyor Python coding agent. Anthropic Claude API'sini ishlatadi,
terminalda interaktiv chat REPL beradi va asosiy fayl operatsiyalari uchun olti
xil tool bilan birga keladi. Boshlash uchun:

```bash
pip install -e .
export ANTHROPIC_API_KEY="sk-ant-..."
shrek
```

## Acknowledgements

- [Practical Coders YouTube channel](https://www.youtube.com/@PracticalCoders) — original walk-through in Uzbek.
- [rahmonov/demo-coding-agent](https://github.com/rahmonov/demo-coding-agent) — the minimal Python prototype this is based on.
- [Amp by Sourcegraph](https://ampcode.com/how-to-build-an-agent) — the seminal Go tutorial that inspired both.
- [Anthropic](https://www.anthropic.com/) for the Claude API and Claude Code.

## License

MIT — see [LICENSE](LICENSE).
