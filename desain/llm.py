"""OpenAI-compatible LLM client factory (local LM Studio + cloud providers)."""

from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from desain.config import Settings

KNOWN_PROVIDERS = {
    "openai": "https://api.openai.com/v1",
    "openai_compatible": None,  # use settings.llm_base_url
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "lmstudio": "http://localhost:1234/v1",
}


@dataclass(frozen=True)
class LlmClientConfig:
    base_url: str
    api_key: str
    provider: str


def resolve_llm_config(settings: Settings) -> LlmClientConfig:
    provider = (settings.llm_provider or "openai_compatible").lower()
    base = KNOWN_PROVIDERS.get(provider)
    if base is None:
        base = settings.llm_base_url
    return LlmClientConfig(
        base_url=base or settings.llm_base_url,
        api_key=settings.llm_api_key or "EMPTY",
        provider=provider,
    )


def create_openai_client(settings: Settings) -> OpenAI:
    cfg = resolve_llm_config(settings)
    return OpenAI(base_url=cfg.base_url, api_key=cfg.api_key)
