import pytest
from pydantic import ValidationError

from desain.photoshop.schemas import AddTextLayerArgs, CreateCanvasArgs, _normalize_hex


def test_normalize_hex_accepts_short_and_namespaced():
    assert _normalize_hex("#fff") == "#FFFFFF"
    assert _normalize_hex("00ff00") == "#00FF00"


def test_normalize_hex_rejects_invalid():
    with pytest.raises(ValueError):
        _normalize_hex("zz")


def test_create_canvas_bounds():
    args = CreateCanvasArgs(width=1080, height=1080, filename="ad")
    assert args.width == 1080
    with pytest.raises(ValidationError):
        CreateCanvasArgs(width=0, height=1080, filename="ad")


def test_add_text_layer_hex_validation():
    args = AddTextLayerArgs(
        content="Hello",
        font_size=48,
        hex_color="#abc",
        x=10,
        y=20,
    )
    assert args.hex_color == "#AABBCC"
