"""High-level Photoshop operations with validation and side effects."""

from __future__ import annotations

import logging
import os
from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from desain.bridge.manager import BridgeManager
from desain.config import Settings
from desain.errors import DesainError, NotFoundError, ValidationError
from desain.photoshop import schemas as S

logger = logging.getLogger(__name__)


def _validate(model: type[BaseModel], payload: dict[str, Any]) -> BaseModel:
    try:
        return model.model_validate(payload)
    except PydanticValidationError as exc:
        raise ValidationError("Invalid tool arguments.", details={"errors": exc.errors()}) from exc


def _result_text(data: dict[str, Any]) -> str:
    if "message" in data and isinstance(data["message"], str):
        return data["message"]
    return str(data)


class PhotoshopService:
    def __init__(self, settings: Settings, bridges: BridgeManager) -> None:
        self.settings = settings
        self.bridges = bridges

    async def bridge_status(self) -> dict[str, Any]:
        status = self.bridges.status()
        bridge = self.bridges.bridge
        if bridge is not None and bridge.is_connected():
            try:
                remote = await self.bridges.call("get_status", mutating=False)
                status["photoshop"] = remote
            except DesainError as exc:
                status["photoshop_error"] = exc.to_dict()
        return status

    async def ping(self) -> dict[str, Any]:
        return await self.bridges.call("ping", mutating=False)

    async def open_template(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.OpenTemplateArgs, kwargs)
        from utils.templates import list_templates, resolve_template_path

        folder = str(self.settings.templates_dir)
        resolved = resolve_template_path(folder, args.filename)
        if not resolved:
            available = list_templates(folder)
            raise NotFoundError(
                f"Template '{args.filename}' not found.",
                details={"available": available, "templates_dir": folder},
            )
        result = await self.bridges.call(
            "open_document",
            {"path": resolved},
            mutating=True,
        )
        ctx = await self.bridges.call("get_layer_context", mutating=False)
        result["path"] = resolved
        result["layer_context"] = ctx
        return result

    async def create_canvas(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.CreateCanvasArgs, kwargs)
        return await self.bridges.call(
            "create_document",
            args.model_dump(),
            mutating=True,
        )

    async def save_document(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.SaveDocumentArgs, kwargs)
        self.settings.output_dir.mkdir(parents=True, exist_ok=True)
        return await self.bridges.call(
            "save_document",
            {
                "filename": args.filename,
                "output_folder": str(self.settings.output_dir),
                "save_psd": args.save_psd,
            },
            mutating=False,
        )

    async def close_document(self, **kwargs: Any) -> dict[str, Any]:
        _validate(S.CloseDocumentArgs, kwargs)
        return await self.bridges.call("close_document", mutating=True)

    async def get_layer_context(self) -> dict[str, Any]:
        return await self.bridges.call("get_layer_context", mutating=False)

    async def add_text_layer(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.AddTextLayerArgs, kwargs)
        return await self.bridges.call("add_text_layer", args.model_dump(), mutating=True)

    async def set_layer_properties(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.SetLayerPropertiesArgs, kwargs)
        return await self.bridges.call(
            "set_layer_properties",
            args.model_dump(exclude_none=True),
            mutating=True,
        )

    async def move_layer(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.MoveLayerArgs, kwargs)
        return await self.bridges.call("move_layer", args.model_dump(), mutating=True)

    async def rotate_layer(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.RotateLayerArgs, kwargs)
        return await self.bridges.call("rotate_layer", args.model_dump(), mutating=True)

    async def scale_layer(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.ScaleLayerArgs, kwargs)
        return await self.bridges.call("scale_layer", args.model_dump(), mutating=True)

    async def reorder_layer(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.ReorderLayerArgs, kwargs)
        return await self.bridges.call("reorder_layer", args.model_dump(), mutating=True)

    async def add_solid_color_layer(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.AddSolidColorArgs, kwargs)
        return await self.bridges.call("add_solid_color_layer", args.model_dump(), mutating=True)

    async def add_gradient_layer(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.AddGradientArgs, kwargs)
        return await self.bridges.call("add_gradient_layer", args.model_dump(), mutating=True)

    async def add_shape(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.AddShapeArgs, kwargs)
        payload = args.model_dump()
        if payload["shape_type"] == "circle":
            side = min(payload["width"], payload["height"])
            payload["shape_type"] = "ellipse"
            payload["width"] = side
            payload["height"] = side
        return await self.bridges.call("add_shape", payload, mutating=True)

    async def change_shape_color(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.ChangeShapeColorArgs, kwargs)
        return await self.bridges.call("change_shape_color", args.model_dump(), mutating=True)

    async def add_stroke(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.AddStrokeArgs, kwargs)
        return await self.bridges.call("add_stroke", args.model_dump(), mutating=True)

    async def _resolve_image(self, keyword: str, path: str | None) -> str:
        if path:
            if not os.path.isfile(path):
                raise NotFoundError(f"Image path not found: {path}")
            return path
        from utils.unsplash import get_image_from_unsplash

        # Temporarily honor env-based key via utils.config override if present.
        img = get_image_from_unsplash(keyword, str(self.settings.output_dir), logger.info)
        if not img:
            raise DesainError(
                code="UNSPLASH_ERROR",
                message="Failed to download image from Unsplash. Set UNSPLASH_ACCESS_KEY.",
                retryable=True,
            )
        return img

    async def add_image_layer(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.AddImageLayerArgs, kwargs)
        path = await self._resolve_image(args.keyword, args.path)
        try:
            return await self.bridges.call(
                "add_image_layer",
                {
                    "path": path,
                    "blend_mode": args.blend_mode,
                    "opacity": args.opacity,
                },
                mutating=True,
            )
        finally:
            if args.path is None and path and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    async def add_element_layer(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.AddElementLayerArgs, kwargs)
        path = await self._resolve_image(args.keyword, args.path)
        try:
            payload = args.model_dump()
            payload["path"] = path
            payload.pop("keyword", None)
            return await self.bridges.call("add_element_layer", payload, mutating=True)
        finally:
            if args.path is None and path and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    async def add_pill_cta(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.AddPillCtaArgs, kwargs)
        return await self.bridges.call(
            "add_pill_cta",
            args.model_dump(exclude_none=True),
            mutating=True,
        )

    async def select_subject_and_mask(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.SelectSubjectArgs, kwargs)
        return await self.bridges.call("select_subject_and_mask", args.model_dump(), mutating=True)

    async def generate_fill(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.GenerateFillArgs, kwargs)
        return await self.bridges.call("generate_fill", args.model_dump(), mutating=True)

    async def history_undo(self, **kwargs: Any) -> dict[str, Any]:
        args = _validate(S.HistoryUndoArgs, kwargs)
        last: dict[str, Any] = {}
        for _ in range(args.steps):
            last = await self.bridges.call("history_undo", mutating=False)
        return last

    async def history_checkpoint(self) -> dict[str, Any]:
        return await self.bridges.call("history_checkpoint", mutating=False)

    async def execute_jsx(self, **kwargs: Any) -> dict[str, Any]:
        if not self.settings.allow_destructive:
            raise ValidationError(
                "execute_jsx is disabled. Set DESAIN_ALLOW_DESTRUCTIVE=true to enable."
            )
        args = _validate(S.ExecuteJsxArgs, kwargs)
        return await self.bridges.call("execute_jsx", args.model_dump(), mutating=True)

    async def execute_batchplay(self, **kwargs: Any) -> dict[str, Any]:
        if not self.settings.allow_destructive:
            raise ValidationError(
                "execute_batchplay is disabled. Set DESAIN_ALLOW_DESTRUCTIVE=true to enable."
            )
        args = _validate(S.ExecuteBatchPlayArgs, kwargs)
        return await self.bridges.call("execute_batchplay", args.model_dump(), mutating=True)

    async def list_templates(self) -> dict[str, Any]:
        from utils.templates import list_templates

        items = list_templates(str(self.settings.templates_dir))
        return {"templates": items, "templates_dir": str(self.settings.templates_dir)}
