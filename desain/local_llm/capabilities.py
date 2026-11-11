"""Model profiling and sensible defaults for small / local models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

ModelSize = Literal["tiny", "small", "medium", "large", "unknown"]
ToolMode = Literal["native", "json_actions", "text_only"]


@dataclass(frozen=True)
class ModelProfile:
    model_id: str
    size: ModelSize
    estimated_params_b: float | None
    tool_mode: ToolMode
    temperature: float
    max_context_messages: int
    max_tool_rounds: int
    prefer_json_schema: bool
    use_few_shot: bool
    step_planning: bool
    self_check: bool
    notes: str = ""


_SIZE_PATTERNS: tuple[tuple[re.Pattern[str], float], ...] = (
    (re.compile(r"(?:^|[^0-9])(0\.5|0\.6|1)b\b", re.I), 1.0),
    (re.compile(r"(?:^|[^0-9])(1\.5|1\.7|1\.8)b\b", re.I), 1.7),
    (re.compile(r"(?:^|[^0-9])(2|2\.5|2\.7)b\b", re.I), 2.5),
    (re.compile(r"(?:^|[^0-9])(3|3\.5)b\b", re.I), 3.0),
    (re.compile(r"(?:^|[^0-9])(4)b\b", re.I), 4.0),
    (re.compile(r"(?:^|[^0-9])(7|7\.1|8|9)b\b", re.I), 7.0),
    (re.compile(r"(?:^|[^0-9])(12|13|14)b\b", re.I), 13.0),
    (re.compile(r"(?:^|[^0-9])(20|22|24|27|30|32|34|70|72|405)b\b", re.I), 30.0),
)

_STRONG_TOOL_HINTS = re.compile(
    r"(gpt-4|gpt-5|claude|qwen2\.5|qwen3|command-r|mistral-small|mistral-large|"
    r"llama-3\.1|llama-3\.3|llama3\.1|llama3\.3|hermes|functionary|toolace)",
    re.I,
)
_WEAK_TOOL_HINTS = re.compile(
    r"(phi-2|phi2|tinyllama|gemma-2b|qwen2-0\.5|qwen2\.5-0\.5|smollm|minicpm)",
    re.I,
)
_VISION_HINTS = re.compile(r"(llava|vision|vl\b|pixtral|qwen2-vl|qwen2\.5-vl)", re.I)


def estimate_params_billions(model_id: str) -> float | None:
    text = model_id.replace("_", "-")
    for pattern, value in _SIZE_PATTERNS:
        if pattern.search(text):
            return value
    return None


def size_bucket(params_b: float | None) -> ModelSize:
    if params_b is None:
        return "unknown"
    if params_b < 2:
        return "tiny"
    if params_b < 5:
        return "small"
    if params_b < 15:
        return "medium"
    return "large"


def profile_model(model_id: str, *, force_tool_mode: ToolMode | None = None) -> ModelProfile:
    """Derive prompting / tool-calling defaults from a model id string."""
    mid = model_id or "local-model"
    params = estimate_params_billions(mid)
    size = size_bucket(params)

    if force_tool_mode:
        tool_mode = force_tool_mode
    elif _WEAK_TOOL_HINTS.search(mid) or size == "tiny":
        tool_mode = "json_actions"
    elif _STRONG_TOOL_HINTS.search(mid) or size in {"medium", "large"}:
        tool_mode = "native"
    elif size == "small":
        tool_mode = "json_actions"
    else:
        # Unknown models: try native first, runtime falls back to JSON actions.
        tool_mode = "native"

    if size == "tiny":
        temperature, ctx, rounds = 0.2, 10, 8
    elif size == "small":
        temperature, ctx, rounds = 0.3, 14, 12
    elif size == "medium":
        temperature, ctx, rounds = 0.4, 20, 18
    elif size == "large":
        temperature, ctx, rounds = 0.5, 28, 24
    else:
        temperature, ctx, rounds = 0.4, 16, 14

    return ModelProfile(
        model_id=mid,
        size=size,
        estimated_params_b=params,
        tool_mode=tool_mode,
        temperature=temperature,
        max_context_messages=ctx,
        max_tool_rounds=rounds,
        prefer_json_schema=tool_mode == "json_actions" or size in {"tiny", "small"},
        use_few_shot=size in {"tiny", "small", "unknown"},
        step_planning=True,
        self_check=size != "tiny",
        notes="vision-capable" if _VISION_HINTS.search(mid) else "",
    )
