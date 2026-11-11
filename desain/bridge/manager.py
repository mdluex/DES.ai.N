"""Bridge selection and lifecycle management."""

from __future__ import annotations

import logging
import sys
from typing import Any

from desain.bridge.base import PhotoshopBridge
from desain.bridge.com_bridge import ComBridge
from desain.bridge.mock_bridge import MockBridge
from desain.bridge.uxp_bridge import UxpBridge
from desain.config import Settings
from desain.errors import BridgeNotConnectedError

logger = logging.getLogger(__name__)


class BridgeManager:
    """Owns the active Photoshop bridge and applies default reliability policy."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.bridge: PhotoshopBridge | None = None

    async def start(self) -> PhotoshopBridge:
        backend = self.settings.bridge_backend
        if backend == "auto":
            # Prefer UXP (cross-platform). COM is Windows-only fallback.
            backend = "uxp"

        if backend == "mock":
            bridge: PhotoshopBridge = MockBridge()
        elif backend == "com":
            bridge = ComBridge()
        elif backend == "uxp":
            bridge = UxpBridge(self.settings)
        else:
            raise ValueError(f"Unknown bridge backend: {backend}")

        await bridge.start()
        self.bridge = bridge
        logger.info("Bridge started backend=%s", bridge.name)
        return bridge

    async def stop(self) -> None:
        if self.bridge is not None:
            await self.bridge.stop()
            self.bridge = None

    def require(self) -> PhotoshopBridge:
        if self.bridge is None:
            raise BridgeNotConnectedError("Bridge manager has not been started.")
        return self.bridge

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        mutating: bool = False,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        bridge = self.require()
        checkpoint = bool(mutating and self.settings.history_checkpoint)
        return await bridge.call(
            method,
            params,
            checkpoint=checkpoint,
            timeout_s=timeout_s or self.settings.bridge_request_timeout_s,
        )

    def status(self) -> dict[str, Any]:
        bridge = self.bridge
        return {
            "backend": None if bridge is None else bridge.name,
            "connected": False if bridge is None else bridge.is_connected(),
            "platform": sys.platform,
            "requested_backend": self.settings.bridge_backend,
        }
