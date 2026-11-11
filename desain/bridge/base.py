"""Abstract Photoshop bridge interface."""

from __future__ import annotations

import abc
from typing import Any


class PhotoshopBridge(abc.ABC):
    """Transport-agnostic Photoshop control surface."""

    name: str = "base"

    @abc.abstractmethod
    async def start(self) -> None:
        """Start listeners / connections."""

    @abc.abstractmethod
    async def stop(self) -> None:
        """Shut down cleanly."""

    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Return True when Photoshop is reachable."""

    @abc.abstractmethod
    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        checkpoint: bool = False,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        """Invoke a Photoshop method and return a result dict."""

    async def ping(self) -> dict[str, Any]:
        return await self.call("ping", {})
