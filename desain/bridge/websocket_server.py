"""WebSocket server that Photoshop UXP plugins connect to as clients.

UXP plugins cannot bind listening sockets, so the MCP process hosts the
WebSocket server and the plugin dials in. This matches the industry pattern
used by open-source Photoshop MCP servers (adb-mcp, drmedia/photoshop-mcp,
CORE-Automate-WSS/photoshop-mcp).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from desain.bridge.protocol import BridgeHello, BridgeRequest, BridgeResponse
from desain.errors import BridgeNotConnectedError, BridgeTimeoutError, PhotoshopError

logger = logging.getLogger(__name__)


class UxpWebSocketHub:
    """Accept one primary UXP client and route request/response pairs."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        request_timeout_s: float = 60.0,
        reconnect_initial_s: float = 1.0,
        reconnect_max_s: float = 30.0,
    ) -> None:
        self.host = host
        self.port = port
        self.request_timeout_s = request_timeout_s
        self.reconnect_initial_s = reconnect_initial_s
        self.reconnect_max_s = reconnect_max_s

        self._server = None
        self._client: ServerConnection | None = None
        self._client_meta: dict[str, Any] = {}
        self._pending: dict[str, asyncio.Future[BridgeResponse]] = {}
        self._lock = asyncio.Lock()
        self._connected = asyncio.Event()

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def client_meta(self) -> dict[str, Any]:
        return dict(self._client_meta)

    async def start(self) -> None:
        if self._server is not None:
            return
        self._server = await serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=20,
            max_size=16 * 1024 * 1024,
        )
        logger.info("UXP WebSocket hub listening on ws://%s:%s", self.host, self.port)

    async def stop(self) -> None:
        # Fail any in-flight requests.
        for fut in list(self._pending.values()):
            if not fut.done():
                fut.set_exception(BridgeNotConnectedError("Bridge shutting down."))
        self._pending.clear()

        if self._client is not None:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None
        self._connected.clear()

        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            logger.info("UXP WebSocket hub stopped.")

    async def wait_until_connected(self, timeout_s: float | None = None) -> bool:
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=timeout_s)
            return True
        except asyncio.TimeoutError:
            return False

    async def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        checkpoint: bool = False,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        if self._client is None:
            raise BridgeNotConnectedError(
                "No UXP plugin connected. Load the DES.ai.N UXP plugin in Photoshop "
                f"and connect to ws://{self.host}:{self.port}."
            )

        req = BridgeRequest(method=method, params=params or {}, checkpoint=checkpoint)
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[BridgeResponse] = loop.create_future()
        self._pending[req.id] = fut

        try:
            payload = req.model_dump_json()
            async with self._lock:
                await self._client.send(payload)
            logger.debug("Sent bridge request %s method=%s", req.id, method)
            resp = await asyncio.wait_for(fut, timeout=timeout_s or self.request_timeout_s)
        except asyncio.TimeoutError as exc:
            self._pending.pop(req.id, None)
            raise BridgeTimeoutError(
                f"Timed out waiting for Photoshop method '{method}'.",
                details={"method": method, "request_id": req.id},
            ) from exc
        except ConnectionClosed as exc:
            self._pending.pop(req.id, None)
            raise BridgeNotConnectedError("UXP plugin disconnected during request.") from exc
        finally:
            self._pending.pop(req.id, None)

        if not resp.ok:
            err = resp.error
            if err is None:
                raise PhotoshopError(f"Photoshop method '{method}' failed.")
            raise PhotoshopError(
                err.message,
                details={"code": err.code, "method": method, **(err.details or {})},
                retryable=err.retryable,
            )
        return resp.result or {}

    async def _handle_client(self, websocket: ServerConnection) -> None:
        remote = getattr(websocket, "remote_address", None)
        logger.info("UXP client connecting from %s", remote)

        # Only keep one active plugin connection.
        if self._client is not None and self._client is not websocket:
            try:
                await self._client.close(code=4000, reason="Superseded by new connection")
            except Exception:
                pass

        self._client = websocket
        self._connected.set()

        try:
            async for raw in websocket:
                await self._on_message(raw)
        except ConnectionClosed:
            logger.warning("UXP client disconnected.")
        finally:
            if self._client is websocket:
                self._client = None
                self._client_meta = {}
                self._connected.clear()
                for fut in list(self._pending.values()):
                    if not fut.done():
                        fut.set_exception(BridgeNotConnectedError("UXP plugin disconnected."))
                self._pending.clear()

    async def _on_message(self, raw: str | bytes) -> None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Ignoring non-JSON bridge message.")
            return

        msg_type = data.get("type")
        if msg_type == "hello":
            try:
                hello = BridgeHello.model_validate(data)
                self._client_meta = hello.model_dump()
                logger.info(
                    "UXP hello: photoshop=%s plugin=%s",
                    hello.photoshop_version,
                    hello.plugin_version,
                )
            except Exception as exc:
                logger.warning("Invalid hello payload: %s", exc)
            return

        if msg_type == "response":
            try:
                resp = BridgeResponse.model_validate(data)
            except Exception as exc:
                logger.warning("Invalid response payload: %s", exc)
                return
            fut = self._pending.get(resp.id)
            if fut and not fut.done():
                fut.set_result(resp)
            else:
                logger.debug("Orphan response id=%s", resp.id)
            return

        if msg_type == "event":
            logger.info("Bridge event: %s", data.get("name") or data)
            return

        logger.debug("Unhandled bridge message type=%s", msg_type)
