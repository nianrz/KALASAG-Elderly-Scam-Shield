from pathlib import Path

import pytest

from app.config import FIXTURE_KB, REAL_KB, Settings, get_settings

ENV_VARS = (
    "LLM_MODEL",
    "LLM_MAX_TOKENS",
    "CONFIDENCE_THRESHOLD",
    "LLM_RETRY_BACKOFF",
    "KB_PATH",
)


@pytest.fixture
def no_shield_env(monkeypatch):
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_defaults_when_nothing_is_set(no_shield_env):
    settings = Settings(_env_file=None)

    assert settings.model_id == "bedrock_converse:global.anthropic.claude-sonnet-5"
    assert settings.max_tokens == 4096
    assert settings.confidence_threshold == 0.70
    assert settings.retry_backoff == 20.0
    expected_kb = REAL_KB if REAL_KB.exists() else FIXTURE_KB
    assert settings.kb_path == expected_kb


def test_reads_every_shield_var(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "bedrock_converse:anthropic.claude-3-5-sonnet")
    monkeypatch.setenv("LLM_MAX_TOKENS", "2048")
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.55")
    monkeypatch.setenv("LLM_RETRY_BACKOFF", "5")
    monkeypatch.setenv("KB_PATH", "/tmp/kb.sqlite")

    settings = Settings(_env_file=None)

    assert settings.model_id == "bedrock_converse:anthropic.claude-3-5-sonnet"
    assert settings.max_tokens == 2048
    assert settings.confidence_threshold == 0.55
    assert settings.retry_backoff == 5.0
    assert settings.kb_path == Path("/tmp/kb.sqlite")


def test_credential_env_vars_do_not_become_settings(monkeypatch, no_shield_env):
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "not-a-setting")

    assert not hasattr(Settings(_env_file=None), "aws_bearer_token_bedrock")


def test_get_settings_is_cached():
    assert get_settings() is get_settings()
