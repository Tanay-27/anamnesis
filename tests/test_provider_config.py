import pytest

from core.provider_config import Provider, get_active_provider


def test_defaults_to_claude_code(monkeypatch):
    monkeypatch.delenv("ANAMNESIS_PROVIDER", raising=False)
    assert get_active_provider() == Provider.CLAUDE_CODE


def test_reads_from_env(monkeypatch):
    monkeypatch.setenv("ANAMNESIS_PROVIDER", "claude_code")
    assert get_active_provider() == Provider.CLAUDE_CODE


def test_unknown_provider_raises_clear_error(monkeypatch):
    monkeypatch.setenv("ANAMNESIS_PROVIDER", "some_unimplemented_provider")
    with pytest.raises(ValueError, match="Unknown ANAMNESIS_PROVIDER"):
        get_active_provider()
