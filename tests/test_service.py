import pytest

from desain.bridge.manager import BridgeManager
from desain.config import Settings
from desain.errors import ValidationError
from desain.photoshop.service import PhotoshopService


@pytest.fixture
async def service(tmp_path):
    settings = Settings(
        bridge_backend="mock",
        templates_dir=tmp_path / "templates",
        output_dir=tmp_path / "output",
        plugins_dir=tmp_path / "plugins",
        history_checkpoint=True,
    )
    settings.templates_dir.mkdir()
    settings.output_dir.mkdir()
    settings.plugins_dir.mkdir()
    # Create a fake template file name only — open_template resolves path existence
    # via templates helper; mock open_document does not need a real PSD.
    (settings.templates_dir / "demo.psd").write_bytes(b"PSD")
    bridges = BridgeManager(settings)
    await bridges.start()
    svc = PhotoshopService(settings, bridges)
    yield svc
    await bridges.stop()


@pytest.mark.asyncio
async def test_create_canvas_and_shape(service: PhotoshopService):
    await service.create_canvas(width=1080, height=1080, filename="ad")
    result = await service.add_shape(
        shape_type="circle",
        x=100,
        y=100,
        width=200,
        height=150,
        hex_color="#ff0000",
    )
    assert "index" in result
    ctx = await service.get_layer_context()
    assert ctx["layers"][0]["bounds"]["width"] == 150  # circle forces equal sides


@pytest.mark.asyncio
async def test_invalid_hex_rejected(service: PhotoshopService):
    await service.create_canvas(width=100, height=100, filename="x")
    with pytest.raises(ValidationError):
        await service.add_solid_color_layer(hex_color="not-a-color")


@pytest.mark.asyncio
async def test_open_template(service: PhotoshopService):
    result = await service.open_template(filename="demo")
    assert "layer_context" in result
    assert result["path"].endswith("demo.psd")


@pytest.mark.asyncio
async def test_list_templates(service: PhotoshopService):
    listing = await service.list_templates()
    assert "demo.psd" in listing["templates"]


@pytest.mark.asyncio
async def test_pill_cta(service: PhotoshopService):
    await service.create_canvas(width=1080, height=1080, filename="cta")
    result = await service.add_pill_cta(
        text="Shop Now",
        x=500,
        y=800,
        width=400,
        height=100,
        pill_color="#ff7a00",
    )
    assert "PILL CTA" in result["message"]
