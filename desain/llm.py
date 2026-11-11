"""LLM client helpers. Local OpenAI-compatible servers are the default path."""

from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from desain.config import Settings
from desain.local_llm.detect import DetectedEndpoint, detect_local_endpoints, pick_best_endpoint
from desain.local_llm.runtime import LocalModelRuntime

# Cloud providers are optional extras — never auto-selected by default.
CLOUD_PROVIDERS = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
}

LOCAL_PROVIDERS = {
    "lmstudio": "http://127.0.0.1:1234/v1",
    "ollama": "http://127.0.0.1:11434/v1",
    "llamacpp": "http://127.0.0.1:8080/v1",
    "openai_compatible": None,  # use settings.llm_base_url
}


@dataclass(frozen=True)
class LlmClientConfig:
    base_url: str
    api_key: str
    provider: str
    is_local: bool = True


def resolve_llm_config(settings: Settings) -> LlmClientConfig:
    provider = (settings.llm_provider or "local").lower()
    if provider in {"auto", "local"}:
        endpoints = detect_local_endpoints(
            preferred_base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "EMPTY",
        )
        best = pick_best_endpoint(endpoints)
        if best:
            return LlmClientConfig(
                base_url=best.base_url,
                api_key=settings.llm_api_key or "EMPTY",
                provider=best.provider,
                is_local=True,
            )
        return LlmClientConfig(
            base_url=settings.llm_base_url or "http://127.0.0.1:1234/v1",
            api_key=settings.llm_api_key or "EMPTY",
            provider="lmstudio",
            is_local=True,
        )

    if provider in CLOUD_PROVIDERS:
        return LlmClientConfig(
            base_url=CLOUD_PROVIDERS[provider],
            api_key=settings.llm_api_key or "EMPTY",
            provider=provider,
            is_local=False,
        )

    base = LOCAL_PROVIDERS.get(provider)
    if base is None:
        base = settings.llm_base_url
    return LlmClientConfig(
        base_url=base or settings.llm_base_url,
        api_key=settings.llm_api_key or "EMPTY",
        provider=provider,
        is_local=provider not in CLOUD_PROVIDERS,
    )


def create_openai_client(settings: Settings) -> OpenAI:
    cfg = resolve_llm_config(settings)
    return OpenAI(base_url=cfg.base_url, api_key=cfg.api_key)


def create_local_runtime(
    settings: Settings,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model_id: str | None = None,
    log=None,
) -> LocalModelRuntime:
    """Factory used by the desktop agent."""
    cfg = resolve_llm_config(settings)
    return LocalModelRuntime(
        base_url=base_url or cfg.base_url,
        api_key=api_key if api_key is not None else cfg.api_key,
        model_id=model_id,
        auto_detect=cfg.is_local,
        log=log,
    )


def list_detected_local_endpoints(settings: Settings) -> list[DetectedEndpoint]:
    return detect_local_endpoints(
        preferred_base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "EMPTY",
    )
