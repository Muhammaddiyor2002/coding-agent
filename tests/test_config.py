"""Tests for runtime configuration loading."""

from __future__ import annotations

from pathlib import Path

from shrek_agent.config import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, Config


def test_defaults(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("SHREK_MODEL", raising=False)
    monkeypatch.delenv("SHREK_MAX_TOKENS", raising=False)
    monkeypatch.delenv("SHREK_BASH_ALLOWLIST", raising=False)
    cfg = Config.from_env(workspace=tmp_path)
    assert cfg.api_key is None
    assert cfg.model == DEFAULT_MODEL
    assert cfg.max_tokens == DEFAULT_MAX_TOKENS
    assert cfg.bash_allow_all is False
    assert cfg.workspace == tmp_path


def test_env_overrides(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("SHREK_MODEL", "claude-opus-4-5")
    monkeypatch.setenv("SHREK_MAX_TOKENS", "1234")
    cfg = Config.from_env(workspace=tmp_path)
    assert cfg.api_key == "sk-test"
    assert cfg.model == "claude-opus-4-5"
    assert cfg.max_tokens == 1234


def test_allowlist_extension(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SHREK_BASH_ALLOWLIST", "make,terraform,docker")
    cfg = Config.from_env(workspace=tmp_path)
    assert "make" in cfg.bash_allowlist
    assert "terraform" in cfg.bash_allowlist
    assert cfg.bash_allow_all is False


def test_allowlist_wildcard(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SHREK_BASH_ALLOWLIST", "*")
    cfg = Config.from_env(workspace=tmp_path)
    assert cfg.bash_allow_all is True


def test_bad_max_tokens_falls_back(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SHREK_MAX_TOKENS", "not-a-number")
    cfg = Config.from_env(workspace=tmp_path)
    assert cfg.max_tokens == DEFAULT_MAX_TOKENS
