import pytest

from desain.bridge.mock_bridge import MockBridge
from desain.errors import NotFoundError, PhotoshopError


@pytest.fixture
async def bridge():
    b = MockBridge()
    await b.start()
    yield b
    await b.stop()


@pytest.mark.asyncio
async def test_ping(bridge: MockBridge):
    result = await bridge.ping()
    assert result["pong"] is True
    assert result["backend"] == "mock"


@pytest.mark.asyncio
async def test_create_and_text_layer(bridge: MockBridge):
    await bridge.call("create_document", {"width": 1080, "height": 1080, "filename": "demo"})
    text = await bridge.call(
        "add_text_layer",
        {
            "content": "Ride",
            "font_size": 90,
            "hex_color": "#FFFFFF",
            "x": 540,
            "y": 400,
            "alignment": "center",
        },
        checkpoint=True,
    )
    assert text["index"] == 0
    ctx = await bridge.call("get_layer_context")
    assert ctx["canvas_w"] == 1080
    assert ctx["layers"][0]["text"] == "Ride"
    assert len(bridge._history) == 1


@pytest.mark.asyncio
async def test_history_undo(bridge: MockBridge):
    await bridge.call("create_document", {"width": 800, "height": 600, "filename": "u"})
    await bridge.call("add_solid_color_layer", {"hex_color": "#000000"}, checkpoint=True)
    await bridge.call("add_text_layer", {"content": "A", "font_size": 20, "hex_color": "#fff", "x": 1, "y": 20})
    ctx = await bridge.call("get_layer_context")
    assert len(ctx["layers"]) == 2
    await bridge.call("history_undo")
    ctx2 = await bridge.call("get_layer_context")
    assert len(ctx2["layers"]) == 0


@pytest.mark.asyncio
async def test_layer_index_error(bridge: MockBridge):
    await bridge.call("create_document", {"width": 100, "height": 100, "filename": "x"})
    with pytest.raises(NotFoundError):
        await bridge.call("move_layer", {"index": 3, "delta_x": 1, "delta_y": 1})


@pytest.mark.asyncio
async def test_requires_document(bridge: MockBridge):
    with pytest.raises(PhotoshopError):
        await bridge.call("get_layer_context")
