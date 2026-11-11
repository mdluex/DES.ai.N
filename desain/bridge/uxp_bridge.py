"""UXP-backed Photoshop bridge."""

from __future__ import annotations

from typing import Any

from desain.bridge.base import PhotoshopBridge
from desain.bridge.websocket_server import UxpWebSocketHub
from desain.config import Settings


class UxpBridge(PhotoshopBridge):
    name = "uxp"

    def __init__(self, settings: Settings, hub: UxpWebSocketHub | None = None) -> None:
        self.settings = settings
        self.hub = hub or UxpWebSocketHub(
            host=settings.bridge_host,
            port=settings.bridge_port,
            request_timeout_s=settings.bridge_request_timeout_s,
            reconnect_initial_s=settings.bridge_reconnect_initial_s,
            reconnect_max_s=settings.bridge_reconnect_max_s,
        )

    async def start(self) -> None:
        await self.hub.start()

    async def stop(self) -> None:
        await self.hub.stop()

    def is_connected(self) -> bool:
        return self.hub.is_connected

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        checkpoint: bool = False,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        return await self.hub.request(
            method,
            params,
            checkpoint=checkpoint,
            timeout_s=timeout_s,
        )
