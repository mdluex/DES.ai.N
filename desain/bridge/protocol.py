"""JSON request/response protocol between the MCP server and Photoshop bridges."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

PROTOCOL_VERSION = 1


class BridgeRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "request"
    method: str
    params: dict[str, Any] = Field(default_factory=dict)
    protocol: int = PROTOCOL_VERSION
    checkpoint: bool = False


class BridgeErrorPayload(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    retryable: bool = False


class BridgeResponse(BaseModel):
    id: str
    type: str = "response"
    ok: bool
    result: dict[str, Any] | None = None
    error: BridgeErrorPayload | None = None
    protocol: int = PROTOCOL_VERSION


class BridgeHello(BaseModel):
    type: str = "hello"
    role: str = "uxp"
    photoshop_version: str | None = None
    plugin_version: str | None = None
    protocol: int = PROTOCOL_VERSION


# Methods the UXP plugin (and COM fallback) must implement.
SUPPORTED_METHODS = frozenset(
    {
        "ping",
        "get_status",
        "open_document",
        "create_document",
        "close_document",
        "save_document",
        "export_png",
        "get_layer_context",
        "add_text_layer",
        "set_layer_properties",
        "move_layer",
        "rotate_layer",
        "scale_layer",
        "reorder_layer",
        "add_solid_color_layer",
        "add_gradient_layer",
        "add_shape",
        "change_shape_color",
        "add_stroke",
        "add_image_layer",
        "add_element_layer",
        "add_pill_cta",
        "select_subject_and_mask",
        "generate_fill",
        "history_checkpoint",
        "history_undo",
        "execute_batchplay",
        "execute_jsx",
    }
)
