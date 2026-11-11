"""Auto-detect local OpenAI-compatible inference servers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

import requests

# Common local OpenAI-compatible bases (in preference order).
DEFAULT_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("lmstudio", "http://127.0.0.1:1234/v1"),
    ("lmstudio", "http://localhost:1234/v1"),
    ("ollama", "http://127.0.0.1:11434/v1"),
    ("ollama", "http://localhost:11434/v1"),
    ("llamacpp", "http://127.0.0.1:8080/v1"),
    ("llamacpp", "http://localhost:8080/v1"),
    ("llamacpp", "http://127.0.0.1:8000/v1"),
    ("openai_compatible", "http://127.0.0.1:5000/v1"),
)


@dataclass(frozen=True)
class DetectedEndpoint:
    provider: str
    base_url: str
    models: list[str] = field(default_factory=list)
    reachable: bool = True
    supports_tools_hint: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def _normalize_base(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if url.endswith("/chat/completions"):
        url = url[: -len("/chat/completions")]
    if not url.endswith("/v1") and url.rstrip("/").endswith(":11434"):
        # Ollama native root — prefer OpenAI-compatible /v1.
        url = url.rstrip("/") + "/v1"
    return url


def probe_endpoint(
    base_url: str,
    *,
    provider: str = "openai_compatible",
    api_key: str = "EMPTY",
    timeout_s: float = 1.5,
) -> DetectedEndpoint | None:
    """Return endpoint metadata if `/models` responds."""
    base = _normalize_base(base_url)
    headers = {"Authorization": f"Bearer {api_key or 'EMPTY'}"}
    try:
        resp = requests.get(urljoin(base + "/", "models"), headers=headers, timeout=timeout_s)
        if resp.status_code >= 400:
            return None
        payload = resp.json() if resp.content else {}
        models: list[str] = []
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("id"):
                    models.append(str(item["id"]))
                elif isinstance(item, str):
                    models.append(item)
        return DetectedEndpoint(
            provider=provider,
            base_url=base,
            models=models,
            reachable=True,
            raw=payload if isinstance(payload, dict) else {},
        )
    except requests.RequestException:
        return None


def detect_local_endpoints(
    *,
    preferred_base_url: str | None = None,
    api_key: str = "EMPTY",
    timeout_s: float = 1.5,
    extra_candidates: list[tuple[str, str]] | None = None,
) -> list[DetectedEndpoint]:
    """Probe known local servers; prefer an explicitly configured base URL."""
    seen: set[str] = set()
    found: list[DetectedEndpoint] = []

    ordered: list[tuple[str, str]] = []
    if preferred_base_url:
        ordered.append(("openai_compatible", preferred_base_url))
    ordered.extend(extra_candidates or [])
    ordered.extend(DEFAULT_CANDIDATES)

    for provider, url in ordered:
        base = _normalize_base(url)
        key = base.lower()
        if key in seen:
            continue
        seen.add(key)
        hit = probe_endpoint(base, provider=provider, api_key=api_key, timeout_s=timeout_s)
        if hit is not None:
            # Preserve preferred provider label when user passed a custom URL that
            # matches a known host.
            labeled = hit
            for known_provider, known_url in DEFAULT_CANDIDATES:
                if _normalize_base(known_url).lower() == key:
                    labeled = DetectedEndpoint(
                        provider=known_provider if provider == "openai_compatible" else provider,
                        base_url=hit.base_url,
                        models=hit.models,
                        reachable=True,
                        raw=hit.raw,
                    )
                    break
            found.append(labeled)
    return found


def pick_best_endpoint(
    endpoints: list[DetectedEndpoint],
    *,
    preferred_model: str | None = None,
) -> DetectedEndpoint | None:
    if not endpoints:
        return None
    if preferred_model:
        for ep in endpoints:
            for mid in ep.models:
                if preferred_model.lower() in mid.lower():
                    return ep
    # Prefer LM Studio, then Ollama, then llama.cpp, then anything reachable.
    priority = {"lmstudio": 0, "ollama": 1, "llamacpp": 2, "openai_compatible": 3}
    return sorted(endpoints, key=lambda e: priority.get(e.provider, 99))[0]
