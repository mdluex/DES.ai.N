import asyncio
import json

import pytest
import websockets

from desain.bridge.websocket_server import UxpWebSocketHub


@pytest.mark.asyncio
async def test_hub_request_roundtrip():
    hub = UxpWebSocketHub(host="127.0.0.1", port=18765, request_timeout_s=5)
    await hub.start()

    async def fake_plugin():
        uri = "ws://127.0.0.1:18765"
        async with websockets.connect(uri) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "hello",
                        "role": "uxp",
                        "photoshop_version": "27.0",
                        "plugin_version": "0.2.0",
                        "protocol": 1,
                    }
                )
            )
            raw = await ws.recv()
            req = json.loads(raw)
            assert req["type"] == "request"
            assert req["method"] == "ping"
            await ws.send(
                json.dumps(
                    {
                        "id": req["id"],
                        "type": "response",
                        "ok": True,
                        "result": {"pong": True},
                        "protocol": 1,
                    }
                )
            )
            # Keep connection briefly so hub can finish.
            await asyncio.sleep(0.1)

    plugin_task = asyncio.create_task(fake_plugin())
    assert await hub.wait_until_connected(timeout_s=3)
    result = await hub.request("ping", {})
    assert result["pong"] is True
    await plugin_task
    await hub.stop()


@pytest.mark.asyncio
async def test_hub_not_connected_error():
    hub = UxpWebSocketHub(host="127.0.0.1", port=18766, request_timeout_s=1)
    await hub.start()
    with pytest.raises(Exception) as exc:
        await hub.request("ping")
    assert "BRIDGE_NOT_CONNECTED" in str(exc.value) or "not connected" in str(exc.value).lower()
    await hub.stop()
