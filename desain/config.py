"""Environment-based configuration. Secrets are never committed."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Load .env from repo root if present (does not override existing env vars).
_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env", override=False)

BridgeBackend = Literal["auto", "uxp", "com", "mock"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    raw = _env(key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = _env(key)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(key: str, default: bool = False) -> bool:
    raw = _env(key).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the MCP server and Photoshop bridge."""

    bridge_backend: BridgeBackend = "auto"
    bridge_host: str = "127.0.0.1"
    bridge_port: int = 8765
    bridge_request_timeout_s: float = 60.0
    bridge_reconnect_initial_s: float = 1.0
    bridge_reconnect_max_s: float = 30.0
    history_checkpoint: bool = True
    log_level: LogLevel = "INFO"
    log_json: bool = False
    templates_dir: Path = field(default_factory=lambda: _REPO_ROOT / "templates")
    output_dir: Path = field(default_factory=lambda: _REPO_ROOT / "output")
    plugins_dir: Path = field(default_factory=lambda: _REPO_ROOT / "plugins")
    unsplash_access_key: str = ""
    llm_base_url: str = "http://localhost:1234/v1"
    llm_api_key: str = ""
    llm_provider: str = "openai_compatible"
    allow_destructive: bool = False

    @classmethod
    def from_env(cls) -> Settings:
        backend = _env("DESAIN_BRIDGE_BACKEND", "auto").lower()
        if backend not in {"auto", "uxp", "com", "mock"}:
            backend = "auto"

        level = _env("DESAIN_LOG_LEVEL", "INFO").upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            level = "INFO"

        templates = _env("DESAIN_TEMPLATES_DIR") or str(_REPO_ROOT / "templates")
        output = _env("DESAIN_OUTPUT_DIR") or str(_REPO_ROOT / "output")
        plugins = _env("DESAIN_PLUGINS_DIR") or str(_REPO_ROOT / "plugins")

        return cls(
            bridge_backend=backend,  # type: ignore[arg-type]
            bridge_host=_env("DESAIN_BRIDGE_HOST", "127.0.0.1") or "127.0.0.1",
            bridge_port=_env_int("DESAIN_BRIDGE_PORT", 8765),
            bridge_request_timeout_s=_env_float("DESAIN_BRIDGE_TIMEOUT_S", 60.0),
            bridge_reconnect_initial_s=_env_float("DESAIN_BRIDGE_RECONNECT_INITIAL_S", 1.0),
            bridge_reconnect_max_s=_env_float("DESAIN_BRIDGE_RECONNECT_MAX_S", 30.0),
            history_checkpoint=_env_bool("DESAIN_HISTORY_CHECKPOINT", True),
            log_level=level,  # type: ignore[arg-type]
            log_json=_env_bool("DESAIN_LOG_JSON", False),
            templates_dir=Path(templates).expanduser().resolve(),
            output_dir=Path(output).expanduser().resolve(),
            plugins_dir=Path(plugins).expanduser().resolve(),
            unsplash_access_key=_env("UNSPLASH_ACCESS_KEY") or _env("UNSPLASH_KEY"),
            llm_base_url=_env("DESAIN_LLM_BASE_URL")
            or _env("OPENAI_BASE_URL")
            or "http://localhost:1234/v1",
            llm_api_key=_env("DESAIN_LLM_API_KEY") or _env("OPENAI_API_KEY") or _env("ANTHROPIC_API_KEY"),
            llm_provider=_env("DESAIN_LLM_PROVIDER", "openai_compatible") or "openai_compatible",
            allow_destructive=_env_bool("DESAIN_ALLOW_DESTRUCTIVE", False),
        )


def get_settings() -> Settings:
    """Return settings loaded from the environment."""
    return Settings.from_env()
