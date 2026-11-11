"""Local-model chat runtime with native tools + JSON-action fallback."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from desain.local_llm.capabilities import ModelProfile, ToolMode, profile_model
from desain.local_llm.detect import DetectedEndpoint, detect_local_endpoints, pick_best_endpoint
from desain.local_llm.json_tools import (
    ParsedToolCall,
    parse_tool_calls_from_text,
    validate_tool_call,
)
from desain.local_llm.prompts import augment_system_prompt, trim_messages

logger = logging.getLogger(__name__)


@dataclass
class RuntimeTurn:
    assistant_text: str | None
    tool_calls: list[ParsedToolCall] = field(default_factory=list)
    mode_used: ToolMode = "native"
    raw_message: Any = None
    done: bool = False
    error: str | None = None


class LocalModelRuntime:
    """Talk to LM Studio / Ollama / llama.cpp with model-aware tool strategies."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str = "EMPTY",
        model_id: str | None = None,
        auto_detect: bool = True,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self.preferred_base_url = base_url
        self.api_key = api_key or "EMPTY"
        self.requested_model_id = model_id
        self.auto_detect = auto_detect
        self.log = log or (lambda _m: None)
        self.endpoint: DetectedEndpoint | None = None
        self.client: OpenAI | None = None
        self.model_id = model_id or "local-model"
        self.profile: ModelProfile = profile_model(self.model_id)
        self._native_tools_failed = False

    def connect(self) -> DetectedEndpoint:
        endpoints: list[DetectedEndpoint] = []
        if self.auto_detect:
            endpoints = detect_local_endpoints(
                preferred_base_url=self.preferred_base_url,
                api_key=self.api_key,
            )
        elif self.preferred_base_url:
            from desain.local_llm.detect import probe_endpoint

            hit = probe_endpoint(
                self.preferred_base_url,
                api_key=self.api_key,
                timeout_s=2.5,
            )
            if hit:
                endpoints = [hit]
            else:
                # Still construct a client against the preferred URL.
                endpoints = [
                    DetectedEndpoint(
                        provider="openai_compatible",
                        base_url=self.preferred_base_url.rstrip("/"),
                        models=[self.requested_model_id] if self.requested_model_id else [],
                    )
                ]

        chosen = pick_best_endpoint(endpoints, preferred_model=self.requested_model_id)
        if chosen is None and self.preferred_base_url:
            chosen = DetectedEndpoint(
                provider="openai_compatible",
                base_url=self.preferred_base_url.rstrip("/"),
                models=[],
            )
        if chosen is None:
            raise RuntimeError(
                "No local LLM endpoint found. Start LM Studio, Ollama, or llama.cpp "
                "with an OpenAI-compatible server, or set DESAIN_LLM_BASE_URL."
            )

        self.endpoint = chosen
        if self.requested_model_id:
            self.model_id = self.requested_model_id
        elif chosen.models:
            self.model_id = chosen.models[0]
        else:
            self.model_id = "local-model"

        self.profile = profile_model(self.model_id)
        self.client = OpenAI(base_url=chosen.base_url, api_key=self.api_key)
        self.log(
            f"[SYSTEM] Local model endpoint: {chosen.provider} @ {chosen.base_url} "
            f"(model={self.model_id}, size={self.profile.size}, mode={self.profile.tool_mode})"
        )
        return chosen

    def ensure_client(self) -> OpenAI:
        if self.client is None:
            self.connect()
        assert self.client is not None
        return self.client

    def prepare_messages(
        self,
        messages: list,
        *,
        tools: list[dict] | None = None,
        json_mode: bool = False,
    ) -> list:
        prepared = list(messages)
        if prepared and isinstance(prepared[0], dict) and prepared[0].get("role") == "system":
            prepared[0] = {
                **prepared[0],
                "content": augment_system_prompt(
                    str(prepared[0].get("content") or ""),
                    self.profile,
                    tools=tools,
                    json_mode=json_mode,
                ),
            }
        return trim_messages(prepared, self.profile.max_context_messages)

    def complete_turn(
        self,
        messages: list,
        tools: list[dict],
        *,
        force_mode: ToolMode | None = None,
    ) -> RuntimeTurn:
        client = self.ensure_client()
        mode: ToolMode = force_mode or self.profile.tool_mode
        if self._native_tools_failed and mode == "native":
            mode = "json_actions"

        if mode == "native":
            turn = self._complete_native(client, messages, tools)
            if turn.error and "tool" in (turn.error or "").lower():
                self._native_tools_failed = True
                self.log("[SYSTEM] Native tool-calling unavailable; falling back to JSON actions.")
                return self._complete_json_actions(client, messages, tools)
            return turn

        if mode == "json_actions":
            return self._complete_json_actions(client, messages, tools)

        # text_only
        prepared = self.prepare_messages(messages, tools=tools, json_mode=False)
        try:
            resp = client.chat.completions.create(
                model=self.model_id,
                messages=prepared,
                temperature=self.profile.temperature,
            )
            content = resp.choices[0].message.content
            return RuntimeTurn(assistant_text=content, mode_used="text_only", raw_message=resp.choices[0].message)
        except Exception as exc:
            return RuntimeTurn(assistant_text=None, mode_used="text_only", error=str(exc))

    def _complete_native(self, client: OpenAI, messages: list, tools: list[dict]) -> RuntimeTurn:
        prepared = self.prepare_messages(messages, tools=tools, json_mode=False)
        try:
            resp = client.chat.completions.create(
                model=self.model_id,
                messages=prepared,
                tools=tools,
                tool_choice="auto",
                temperature=self.profile.temperature,
            )
        except Exception as exc:
            return RuntimeTurn(assistant_text=None, mode_used="native", error=str(exc))

        message = resp.choices[0].message
        calls: list[ParsedToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    from desain.local_llm.json_tools import repair_json_text

                    try:
                        args = json.loads(repair_json_text(tc.function.arguments or "{}"))
                    except json.JSONDecodeError:
                        args = {}
                ok, err, cleaned = validate_tool_call(tc.function.name, args if isinstance(args, dict) else {})
                if not ok:
                    self.log(f"[SYSTEM] Dropping invalid native tool call: {err}")
                    continue
                calls.append(ParsedToolCall(tc.function.name, cleaned, source="native"))
        return RuntimeTurn(
            assistant_text=message.content,
            tool_calls=calls,
            mode_used="native",
            raw_message=message,
            done=not calls and bool(message.content),
        )

    def _complete_json_actions(
        self, client: OpenAI, messages: list, tools: list[dict]
    ) -> RuntimeTurn:
        prepared = self.prepare_messages(messages, tools=tools, json_mode=True)
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "messages": prepared,
            "temperature": self.profile.temperature,
        }
        # Some local servers honor response_format / grammar-like JSON mode.
        if self.profile.prefer_json_schema:
            kwargs["response_format"] = {"type": "json_object"}

        content = None
        last_error = None
        for attempt in range(2):
            try:
                try:
                    resp = client.chat.completions.create(**kwargs)
                except Exception:
                    # Retry without response_format if the server rejects it.
                    kwargs.pop("response_format", None)
                    resp = client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""
                calls, message, done = parse_tool_calls_from_text(content)
                if calls or done or message:
                    valid_calls: list[ParsedToolCall] = []
                    for call in calls:
                        ok, err, cleaned = validate_tool_call(call.name, call.arguments)
                        if ok:
                            valid_calls.append(
                                ParsedToolCall(call.name, cleaned, source=call.source)
                            )
                        else:
                            self.log(f"[SYSTEM] Invalid JSON action skipped: {err}")
                    return RuntimeTurn(
                        assistant_text=message or (content if not valid_calls else None),
                        tool_calls=valid_calls,
                        mode_used="json_actions",
                        raw_message=resp.choices[0].message,
                        done=done and not valid_calls,
                    )
                # Empty parse — ask model to repair on next attempt by appending nudge.
                if attempt == 0:
                    prepared = prepared + [
                        {
                            "role": "user",
                            "content": (
                                "Your previous reply was not valid JSON. "
                                "Reply again with ONLY the JSON object schema."
                            ),
                        }
                    ]
                    continue
            except Exception as exc:
                last_error = str(exc)
                break

        # Last resort: try to parse whatever we got.
        if content:
            calls, message, done = parse_tool_calls_from_text(content)
            return RuntimeTurn(
                assistant_text=message or content,
                tool_calls=calls,
                mode_used="json_actions",
                done=done,
                error=last_error,
            )
        return RuntimeTurn(assistant_text=None, mode_used="json_actions", error=last_error or "empty response")
