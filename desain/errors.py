"""Typed error model used across the bridge and MCP tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DesainError(Exception):
    """Base error with a stable machine-readable code."""

    code: str
    message: str
    details: dict[str, Any] | None = None
    retryable: bool = False

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class ValidationError(DesainError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(code="VALIDATION_ERROR", message=message, details=details)


class BridgeNotConnectedError(DesainError):
    def __init__(self, message: str = "Photoshop bridge is not connected."):
        super().__init__(code="BRIDGE_NOT_CONNECTED", message=message, retryable=True)


class BridgeTimeoutError(DesainError):
    def __init__(self, message: str = "Photoshop bridge request timed out.", details: dict[str, Any] | None = None):
        super().__init__(code="BRIDGE_TIMEOUT", message=message, details=details, retryable=True)


class PhotoshopError(DesainError):
    def __init__(self, message: str, details: dict[str, Any] | None = None, retryable: bool = False):
        super().__init__(code="PHOTOSHOP_ERROR", message=message, details=details, retryable=retryable)


class NotFoundError(DesainError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(code="NOT_FOUND", message=message, details=details)
