from pathlib import Path

from desain.config import Settings
from desain.plugins.loader import load_plugins


def test_settings_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DESAIN_BRIDGE_BACKEND", "mock")
    monkeypatch.setenv("DESAIN_BRIDGE_PORT", "9999")
    monkeypatch.setenv("DESAIN_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "test-key")
    monkeypatch.setenv("DESAIN_TEMPLATES_DIR", str(tmp_path / "t"))
    settings = Settings.from_env()
    assert settings.bridge_backend == "mock"
    assert settings.bridge_port == 9999
    assert settings.log_level == "DEBUG"
    assert settings.unsplash_access_key == "test-key"


def test_load_example_plugin():
    root = Path(__file__).resolve().parents[1]
    tools = load_plugins(root / "plugins")
    names = {t.name for t in tools}
    assert "example_echo" in names


def test_no_committed_secrets_in_config_source():
    root = Path(__file__).resolve().parents[1]
    text = (root / "utils" / "config.py").read_text(encoding="utf-8")
    assert "Xuiob-" not in text
    assert "sk-lm-" not in text
