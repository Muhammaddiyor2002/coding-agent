"""Tests for the Agent loop with a fake Anthropic client."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from shrek_agent.agent import Agent
from shrek_agent.config import Config


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class FakeMessage:
    content: list[Any]


class FakeClient:
    """Replay a queued list of FakeMessage instances on each .messages.create call."""

    def __init__(self, responses: list[FakeMessage]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

        class _Messages:
            def __init__(self, outer: FakeClient) -> None:
                self._outer = outer

            def create(self, **kwargs: Any) -> FakeMessage:
                self._outer.calls.append(kwargs)
                return self._outer._responses.pop(0)

        self.messages = _Messages(self)


@pytest.fixture()
def config(tmp_path: Path) -> Config:
    return Config(api_key="test", model="claude-sonnet-4-5", max_tokens=1024, workspace=tmp_path)


def test_text_only_response(config: Config) -> None:
    client = FakeClient([FakeMessage(content=[FakeTextBlock(text="hi there")])])
    agent = Agent(config=config, client=client)  # type: ignore[arg-type]
    agent.send("hello")
    assert client.calls[0]["model"] == "claude-sonnet-4-5"
    assert len(agent.conversation) == 2  # user + assistant


def test_tool_use_round_trip(config: Config) -> None:
    (config.workspace / "x.txt").write_text("payload", encoding="utf-8")
    client = FakeClient(
        [
            FakeMessage(
                content=[
                    FakeTextBlock(text="reading file"),
                    FakeToolUseBlock(id="t1", name="read_file", input={"path": "x.txt"}),
                ]
            ),
            FakeMessage(content=[FakeTextBlock(text="file says payload")]),
        ]
    )
    agent = Agent(config=config, client=client)  # type: ignore[arg-type]
    agent.send("what's in x.txt?")
    # user, assistant(text+tool_use), user(tool_result), assistant(text)
    assert len(agent.conversation) == 4
    tool_results = agent.conversation[2]["content"]
    assert tool_results[0]["type"] == "tool_result"
    assert tool_results[0]["content"] == "payload"
    assert tool_results[0]["is_error"] is False


def test_unknown_tool_is_error(config: Config) -> None:
    client = FakeClient(
        [
            FakeMessage(content=[FakeToolUseBlock(id="t1", name="does_not_exist", input={})]),
            FakeMessage(content=[FakeTextBlock(text="ok")]),
        ]
    )
    agent = Agent(config=config, client=client)  # type: ignore[arg-type]
    agent.send("call missing tool")
    tool_result = agent.conversation[2]["content"][0]
    assert tool_result["is_error"] is True
    assert "not registered" in tool_result["content"]


def test_reset(config: Config) -> None:
    client = FakeClient([FakeMessage(content=[FakeTextBlock(text="x")])])
    agent = Agent(config=config, client=client)  # type: ignore[arg-type]
    agent.send("hi")
    assert agent.conversation
    agent.reset()
    assert not agent.conversation
