"""Local / offline LLM helpers for the DES.ai.N desktop agent."""

from desain.local_llm.capabilities import ModelProfile, profile_model
from desain.local_llm.detect import DetectedEndpoint, detect_local_endpoints
from desain.local_llm.json_tools import (
    ParsedToolCall,
    extract_json_payload,
    parse_tool_calls_from_text,
    repair_json_text,
    validate_tool_call,
)
from desain.local_llm.runtime import LocalModelRuntime, RuntimeTurn

__all__ = [
    "DetectedEndpoint",
    "LocalModelRuntime",
    "ModelProfile",
    "ParsedToolCall",
    "RuntimeTurn",
    "detect_local_endpoints",
    "extract_json_payload",
    "parse_tool_calls_from_text",
    "profile_model",
    "repair_json_text",
    "validate_tool_call",
]
