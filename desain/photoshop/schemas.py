"""Pydantic schemas for MCP tool inputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _normalize_hex(value: str) -> str:
    raw = value.strip()
    if not raw.startswith("#"):
        raw = f"#{raw}"
    if len(raw) == 4:
        raw = "#" + "".join(ch * 2 for ch in raw[1:])
    if len(raw) != 7:
        raise ValueError("Color must be a #RRGGBB hex value")
    int(raw[1:], 16)
    return raw.upper()


class HexColor(BaseModel):
    hex_color: str

    @field_validator("hex_color")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        return _normalize_hex(v)


class OpenTemplateArgs(BaseModel):
    filename: str = Field(..., min_length=1, description="Template filename or substring (.psd/.psb)")


class CreateCanvasArgs(BaseModel):
    width: int = Field(..., ge=1, le=300000)
    height: int = Field(..., ge=1, le=300000)
    filename: str = Field(..., min_length=1, max_length=200)


class SaveDocumentArgs(BaseModel):
    filename: str = Field(..., min_length=1, max_length=200)
    save_psd: bool = False


class CloseDocumentArgs(BaseModel):
    pass


class AddTextLayerArgs(BaseModel):
    content: str = Field(..., min_length=1)
    font_size: int = Field(..., ge=1, le=2000)
    hex_color: str
    x: int
    y: int
    alignment: Literal["left", "center", "right"] = "left"
    blend_mode: int = Field(1, ge=1, le=23)
    opacity: int = Field(100, ge=0, le=100)
    font_name: str | None = None
    rotation: float = 0
    letter_spacing: float | None = None

    @field_validator("hex_color")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        return _normalize_hex(v)


class SetLayerPropertiesArgs(BaseModel):
    index: int = Field(..., ge=0)
    text: str | None = None
    font_size: int | None = Field(None, ge=1, le=2000)
    font_name: str | None = None
    hex_color: str | None = None
    opacity: int | None = Field(None, ge=0, le=100)
    blend_mode: int | None = Field(None, ge=1, le=23)

    @field_validator("hex_color")
    @classmethod
    def validate_hex(cls, v: str | None) -> str | None:
        return None if v is None else _normalize_hex(v)


class MoveLayerArgs(BaseModel):
    index: int = Field(..., ge=0)
    delta_x: int
    delta_y: int


class RotateLayerArgs(BaseModel):
    index: int = Field(..., ge=0)
    angle: float


class ScaleLayerArgs(BaseModel):
    index: int = Field(..., ge=0)
    scale_percent: float = Field(..., gt=0, le=10000)


class ReorderLayerArgs(BaseModel):
    index: int = Field(..., ge=0)
    new_index: int = Field(..., ge=0)


class AddSolidColorArgs(BaseModel):
    hex_color: str
    blend_mode: int = Field(1, ge=1, le=23)
    opacity: int = Field(100, ge=0, le=100)

    @field_validator("hex_color")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        return _normalize_hex(v)


class AddGradientArgs(BaseModel):
    hex_color1: str
    hex_color2: str
    angle: int = 90
    blend_mode: int = Field(1, ge=1, le=23)
    opacity: int = Field(100, ge=0, le=100)

    @field_validator("hex_color1", "hex_color2")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        return _normalize_hex(v)


class AddShapeArgs(BaseModel):
    shape_type: Literal["rectangle", "ellipse", "circle"]
    x: int
    y: int
    width: int = Field(..., ge=1)
    height: int = Field(..., ge=1)
    hex_color: str
    corner_radius: int = Field(0, ge=0)
    opacity: int = Field(100, ge=0, le=100)
    rotation: float = 0

    @field_validator("hex_color")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        return _normalize_hex(v)


class ChangeShapeColorArgs(BaseModel):
    index: int = Field(..., ge=0)
    hex_color: str

    @field_validator("hex_color")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        return _normalize_hex(v)


class AddStrokeArgs(BaseModel):
    index: int = Field(..., ge=0)
    thickness: int = Field(..., ge=1, le=500)
    hex_color: str

    @field_validator("hex_color")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        return _normalize_hex(v)


class AddImageLayerArgs(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=120)
    blend_mode: int = Field(1, ge=1, le=23)
    opacity: int = Field(100, ge=0, le=100)
    path: str | None = Field(None, description="Optional local image path; skips Unsplash when set")


class AddElementLayerArgs(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=120)
    x: int
    y: int
    width: int = Field(..., ge=1)
    height: int = Field(..., ge=1)
    remove_background: bool = False
    blend_mode: int = Field(1, ge=1, le=23)
    opacity: int = Field(100, ge=0, le=100)
    rotation: float = 0
    path: str | None = None


class AddPillCtaArgs(BaseModel):
    text: str = Field(..., min_length=1, max_length=80)
    x: int
    y: int
    width: int = Field(..., ge=1)
    height: int = Field(..., ge=1)
    pill_color: str
    text_color: str = "#FFFFFF"
    font_size: int | None = Field(None, ge=1, le=2000)
    font_name: str | None = None
    corner_radius: int | None = Field(None, ge=0)

    @field_validator("pill_color", "text_color")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        return _normalize_hex(v)


class SelectSubjectArgs(BaseModel):
    index: int = Field(..., ge=0)


class GenerateFillArgs(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    x: int
    y: int
    width: int = Field(..., ge=1)
    height: int = Field(..., ge=1)


class HistoryUndoArgs(BaseModel):
    steps: int = Field(1, ge=1, le=50)


class ExecuteJsxArgs(BaseModel):
    script: str = Field(..., min_length=1, max_length=100_000)


class ExecuteBatchPlayArgs(BaseModel):
    commands: list[dict] = Field(..., min_length=1)
