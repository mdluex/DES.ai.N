"""Structured JSON tool-call parsing, repair, and validation for local models."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, ValidationError

KNOWN_TOOL_NAMES = frozenset(
    {
        "open_template",
        "create_canvas",
        "save_document",
        "close_document",
        "add_image_layer",
        "add_solid_color_layer",
        "add_gradient_layer",
        "add_shape",
        "add_text_layer",
        "set_layer_properties",
        "move_layer",
        "rotate_layer",
        "scale_layer",
        "add_stroke",
        "reorder_layer",
        "select_subject_and_mask",
        "add_element_layer",
        "generate_fill",
        "change_shape_color",
        "add_pill_cta",
        "finalize_design",
        "get_layer_context",
        "history_checkpoint",
        "history_undo",
    }
)


class ActionItem(BaseModel):
    tool: str = Field(..., min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ActionPlan(BaseModel):
    """Canonical JSON plan for models that cannot do native tool-calling."""

    thinking: str | None = None
    actions: list[ActionItem] = Field(default_factory=list)
    message: str | None = None
    done: bool = False


@dataclass(frozen=True)
class ParsedToolCall:
    name: str
    arguments: dict[str, Any]
    source: str = "json"  # json | native | repaired


_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*([\s\S]*?)```")
_BALANCED_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def extract_json_payload(text: str) -> str | None:
    """Pull the most likely JSON object/array out of free-form model text."""
    if not text or not text.strip():
        return None
    stripped = text.strip()

    fence = _FENCE_RE.search(stripped)
    if fence:
        candidate = fence.group(1).strip()
        if candidate:
            return candidate

    # Prefer a top-level object containing "actions" or "tool".
    for match in re.finditer(r"\{[\s\S]*\}", stripped):
        chunk = match.group(0)
        if '"actions"' in chunk or '"tool"' in chunk or '"name"' in chunk:
            return chunk

    arr = re.search(r"\[[\s\S]*\]", stripped)
    if arr:
        return arr.group(0)

    obj = _BALANCED_OBJECT_RE.search(stripped)
    return obj.group(0) if obj else None


def repair_json_text(text: str) -> str:
    """Best-effort repair of common local-model JSON mistakes."""
    s = text.strip()
    if not s:
        return s

    # Unicode quotes → ASCII
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    # Trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)
    # Single-quoted keys
    s = re.sub(r"(?<=\{|,)\s*'([^']+)'\s*:", r' "\1":', s)
    # Single-quoted string values (simple)
    s = re.sub(r":\s*'([^']*)'", r': "\1"', s)
    # True/False/None pythonisms
    s = re.sub(r"\bTrue\b", "true", s)
    s = re.sub(r"\bFalse\b", "false", s)
    s = re.sub(r"\bNone\b", "null", s)
    # Remove JS-style comments
    s = re.sub(r"//.*?$", "", s, flags=re.M)
    s = re.sub(r"/\*[\s\S]*?\*/", "", s)

    # Balance braces/brackets if obviously truncated.
    opens = s.count("{") - s.count("}")
    if opens > 0:
        s += "}" * opens
    opens_b = s.count("[") - s.count("]")
    if opens_b > 0:
        s += "]" * opens_b

    return s.strip()


def _loads_maybe_repaired(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        repaired = repair_json_text(raw)
        return json.loads(repaired)


def _normalize_action_dict(item: dict[str, Any]) -> dict[str, Any] | None:
    name = item.get("tool") or item.get("name") or item.get("function")
    if isinstance(name, dict):
        # {"function": {"name": "...", "arguments": {...}}}
        name = name.get("name")
        args = item.get("function", {}).get("arguments") or item.get("arguments") or {}
    else:
        args = item.get("arguments") or item.get("args") or item.get("parameters") or {}

    if not name or not isinstance(name, str):
        return None
    if isinstance(args, str):
        try:
            args = _loads_maybe_repaired(args)
        except json.JSONDecodeError:
            args = {}
    if not isinstance(args, dict):
        args = {}
    return {"tool": name.strip(), "arguments": args}


def parse_tool_calls_from_text(text: str) -> tuple[list[ParsedToolCall], str | None, bool]:
    """Parse an action plan from model text.

    Returns (tool_calls, assistant_message, done_flag).
    """
    payload = extract_json_payload(text)
    if payload is None:
        return [], text.strip() or None, False

    try:
        data = _loads_maybe_repaired(payload)
        repaired = data is not None and payload != repair_json_text(payload)
        source = "repaired" if repaired else "json"
    except json.JSONDecodeError:
        return [], text.strip() or None, False

    calls: list[ParsedToolCall] = []
    message: str | None = None
    done = False

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                norm = _normalize_action_dict(item)
                if norm:
                    calls.append(ParsedToolCall(norm["tool"], norm["arguments"], source=source))
        return calls, None, False

    if not isinstance(data, dict):
        return [], text.strip() or None, False

    # Single tool shorthand: {"tool": "...", "arguments": {...}}
    if "tool" in data or "name" in data:
        if "actions" not in data:
            norm = _normalize_action_dict(data)
            if norm:
                calls.append(ParsedToolCall(norm["tool"], norm["arguments"], source=source))
            return calls, data.get("message"), bool(data.get("done", False))

    try:
        plan = ActionPlan.model_validate(data)
        for action in plan.actions:
            calls.append(ParsedToolCall(action.tool, action.arguments, source=source))
        return calls, plan.message or plan.thinking, plan.done
    except ValidationError:
        actions = data.get("actions") or data.get("tool_calls") or data.get("steps") or []
        if isinstance(actions, list):
            for item in actions:
                if isinstance(item, dict):
                    norm = _normalize_action_dict(item)
                    if norm:
                        calls.append(
                            ParsedToolCall(norm["tool"], norm["arguments"], source=source)
                        )
        message = data.get("message") or data.get("thinking")
        done = bool(data.get("done", False))
        return calls, message if isinstance(message, str) else None, done


def validate_tool_call(
    name: str,
    arguments: dict[str, Any],
    *,
    known_tools: set[str] | frozenset[str] | None = None,
) -> tuple[bool, str | None, dict[str, Any]]:
    """Light structural validation before dispatching a tool."""
    tools = known_tools or KNOWN_TOOL_NAMES
    if name not in tools:
        return False, f"Unknown tool '{name}'.", arguments
    if not isinstance(arguments, dict):
        return False, "Arguments must be an object.", {}

    # Required-key checks for high-traffic tools.
    required = {
        "open_template": ["filename"],
        "create_canvas": ["width", "height", "filename"],
        "add_text_layer": ["content", "font_size", "hex_color", "x", "y"],
        "move_layer": ["index", "delta_x", "delta_y"],
        "finalize_design": ["message", "filename"],
        "add_shape": ["shape_type", "x", "y", "width", "height", "hex_color"],
        "add_pill_cta": ["text", "x", "y", "width", "height", "pill_color"],
    }
    missing = [k for k in required.get(name, []) if k not in arguments]
    if missing:
        return False, f"Missing required arguments: {', '.join(missing)}.", arguments
    return True, None, arguments


def build_json_action_schema_prompt(tool_summaries: list[dict[str, str]]) -> str:
    """Compact schema instructions for JSON-action mode."""
    lines = [
        "Respond with a single JSON object only. No markdown fences.",
        'Schema: {"thinking": string, "actions": [{"tool": string, "arguments": object}], '
        '"message": string, "done": boolean}',
        "Put 1-3 actions per response. Set done=true only when the design is finished.",
        "Available tools:",
    ]
    for tool in tool_summaries:
        lines.append(f"- {tool['name']}: {tool['description']}")
    lines.extend(
        [
            "Example:",
            '{"thinking":"Create a square canvas then add a headline",'
            '"actions":['
            '{"tool":"create_canvas","arguments":{"width":1080,"height":1080,"filename":"ad"}},'
            '{"tool":"add_text_layer","arguments":{"content":"Hello","font_size":72,'
            '"hex_color":"#FFFFFF","x":540,"y":400,"alignment":"center"}}'
            '],"message":"Starting layout","done":false}',
        ]
    )
    return "\n".join(lines)
