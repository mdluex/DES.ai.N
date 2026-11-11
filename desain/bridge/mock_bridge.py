"""In-memory Photoshop bridge for unit tests and CI."""

from __future__ import annotations

import copy
from typing import Any

from desain.bridge.base import PhotoshopBridge
from desain.errors import NotFoundError, PhotoshopError, ValidationError


class MockBridge(PhotoshopBridge):
    name = "mock"

    def __init__(self) -> None:
        self._connected = False
        self._doc: dict[str, Any] | None = None
        self._history: list[dict[str, Any]] = []
        self._next_id = 1
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def start(self) -> None:
        self._connected = True

    async def stop(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def _require_doc(self) -> dict[str, Any]:
        if self._doc is None:
            raise PhotoshopError("No active document.")
        return self._doc

    def _snapshot(self) -> None:
        if self._doc is not None:
            self._history.append(copy.deepcopy(self._doc))

    def _layer(self, index: int) -> dict[str, Any]:
        doc = self._require_doc()
        layers = doc["layers"]
        if index < 0 or index >= len(layers):
            raise NotFoundError(f"Layer index {index} out of bounds.", details={"index": index})
        return layers[index]

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        checkpoint: bool = False,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        if not self._connected:
            raise PhotoshopError("Mock bridge not started.")
        params = params or {}
        self.calls.append((method, dict(params)))
        if checkpoint:
            self._snapshot()

        handler = getattr(self, f"_op_{method}", None)
        if handler is None:
            raise ValidationError(f"Unsupported method: {method}")
        result = handler(params)
        return result if isinstance(result, dict) else {"ok": True}

    def _op_ping(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"pong": True, "backend": "mock"}

    def _op_get_status(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "connected": True,
            "backend": "mock",
            "has_document": self._doc is not None,
            "document_name": None if self._doc is None else self._doc.get("name"),
        }

    def _op_create_document(self, params: dict[str, Any]) -> dict[str, Any]:
        width = int(params.get("width", 1080))
        height = int(params.get("height", 1080))
        name = str(params.get("filename") or params.get("name") or "Untitled")
        self._doc = {
            "name": name,
            "width": width,
            "height": height,
            "layers": [],
        }
        return {"message": f"Canvas created successfully. Resolution: {width}x{height}.", "width": width, "height": height}

    def _op_open_document(self, params: dict[str, Any]) -> dict[str, Any]:
        path = params.get("path")
        if not path:
            raise ValidationError("path is required")
        self._doc = {
            "name": str(path).split("/")[-1].split("\\")[-1],
            "width": int(params.get("width", 1080)),
            "height": int(params.get("height", 1080)),
            "path": path,
            "layers": [
                {
                    "index": 0,
                    "name": "Background",
                    "kind": "normal",
                    "opacity": 100,
                    "blend_mode": "Normal",
                    "visible": True,
                    "bounds": {"left": 0, "top": 0, "right": 1080, "bottom": 1080, "width": 1080, "height": 1080, "center_x": 540, "center_y": 540},
                }
            ],
        }
        return {"message": "Document opened successfully.", "path": path}

    def _op_close_document(self, params: dict[str, Any]) -> dict[str, Any]:
        self._doc = None
        return {"message": "Document closed without saving."}

    def _op_save_document(self, params: dict[str, Any]) -> dict[str, Any]:
        self._require_doc()
        filename = params.get("filename", "saved_design")
        return {"message": f"Saved as {filename}.png (document still open for further edits).", "filename": filename}

    def _op_export_png(self, params: dict[str, Any]) -> dict[str, Any]:
        self._require_doc()
        return {"message": "Preview exported.", "path": params.get("path")}

    def _op_get_layer_context(self, params: dict[str, Any]) -> dict[str, Any]:
        doc = self._require_doc()
        return {
            "resolution": f"{doc['width']}x{doc['height']}",
            "canvas_w": doc["width"],
            "canvas_h": doc["height"],
            "layers": list(doc["layers"]),
            "fonts_used": sorted(
                {layer.get("font") for layer in doc["layers"] if layer.get("font")}
            ),
        }

    def _append_layer(self, layer: dict[str, Any]) -> dict[str, Any]:
        doc = self._require_doc()
        layer = dict(layer)
        layer["index"] = len(doc["layers"])
        doc["layers"].append(layer)
        return layer

    def _op_add_text_layer(self, params: dict[str, Any]) -> dict[str, Any]:
        content = params.get("content", "Text")
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        size = int(params.get("font_size", 72))
        layer = self._append_layer(
            {
                "name": str(content)[:32],
                "kind": "text",
                "text": content,
                "font_size": size,
                "font": params.get("font_name") or "Arial",
                "color_hex": params.get("hex_color", "#FFFFFF"),
                "alignment": params.get("alignment", "left"),
                "opacity": int(params.get("opacity", 100)),
                "blend_mode": "Normal",
                "visible": True,
                "text_position": [x, y],
                "bounds": {
                    "left": x,
                    "top": max(0, y - size),
                    "right": x + max(40, len(str(content)) * size // 2),
                    "bottom": y + int(size * 0.2),
                    "width": max(40, len(str(content)) * size // 2),
                    "height": int(size * 1.2),
                    "center_x": x,
                    "center_y": y,
                },
            }
        )
        return {"message": f"Text layer added successfully at index {layer['index']}.", "index": layer["index"], "bounds": layer["bounds"]}

    def _op_set_layer_properties(self, params: dict[str, Any]) -> dict[str, Any]:
        layer = self._layer(int(params["index"]))
        for key in ("text", "font_size", "opacity", "font_name", "hex_color"):
            if key in params and params[key] is not None:
                if key == "font_name":
                    layer["font"] = params[key]
                elif key == "hex_color":
                    layer["color_hex"] = params[key]
                else:
                    layer[key] = params[key]
        return {"message": f"Layer {params['index']} properties updated.", "bounds": layer.get("bounds")}

    def _op_move_layer(self, params: dict[str, Any]) -> dict[str, Any]:
        layer = self._layer(int(params["index"]))
        dx = int(params.get("delta_x", 0))
        dy = int(params.get("delta_y", 0))
        b = layer.setdefault("bounds", {})
        for k in ("left", "right", "center_x"):
            if k in b:
                b[k] = int(b[k]) + dx
        for k in ("top", "bottom", "center_y"):
            if k in b:
                b[k] = int(b[k]) + dy
        return {"message": f"Layer {params['index']} moved by ({dx},{dy}).", "bounds": b}

    def _op_rotate_layer(self, params: dict[str, Any]) -> dict[str, Any]:
        layer = self._layer(int(params["index"]))
        layer["rotation"] = float(params.get("angle", 0))
        return {"message": f"Layer {params['index']} rotated.", "bounds": layer.get("bounds")}

    def _op_scale_layer(self, params: dict[str, Any]) -> dict[str, Any]:
        layer = self._layer(int(params["index"]))
        scale = float(params.get("scale_percent", 100))
        b = layer.get("bounds") or {}
        if b:
            cx, cy = b.get("center_x", 0), b.get("center_y", 0)
            w = int(b.get("width", 0) * scale / 100)
            h = int(b.get("height", 0) * scale / 100)
            layer["bounds"] = {
                "left": cx - w // 2,
                "top": cy - h // 2,
                "right": cx + w // 2,
                "bottom": cy + h // 2,
                "width": w,
                "height": h,
                "center_x": cx,
                "center_y": cy,
            }
        return {"message": f"Layer {params['index']} scaled to {scale}%.", "bounds": layer.get("bounds")}

    def _op_reorder_layer(self, params: dict[str, Any]) -> dict[str, Any]:
        doc = self._require_doc()
        src = int(params["index"])
        dst = int(params["new_index"])
        layer = doc["layers"].pop(src)
        doc["layers"].insert(dst, layer)
        for i, lyr in enumerate(doc["layers"]):
            lyr["index"] = i
        return {"message": f"Layer moved from index {src} to {dst}."}

    def _op_add_solid_color_layer(self, params: dict[str, Any]) -> dict[str, Any]:
        layer = self._append_layer(
            {
                "name": f"Color Fill {params.get('hex_color', '#000000')}",
                "kind": "solid",
                "opacity": int(params.get("opacity", 100)),
                "blend_mode": "Normal",
                "visible": True,
                "color_hex": params.get("hex_color", "#000000"),
            }
        )
        return {"message": f"Solid color layer added successfully at index {layer['index']}.", "index": layer["index"]}

    def _op_add_gradient_layer(self, params: dict[str, Any]) -> dict[str, Any]:
        layer = self._append_layer(
            {
                "name": "Gradient",
                "kind": "gradient",
                "opacity": int(params.get("opacity", 100)),
                "blend_mode": "Normal",
                "visible": True,
            }
        )
        return {"message": f"Gradient layer added successfully at index {layer['index']}.", "index": layer["index"]}

    def _op_add_shape(self, params: dict[str, Any]) -> dict[str, Any]:
        x, y = int(params.get("x", 0)), int(params.get("y", 0))
        w, h = int(params.get("width", 100)), int(params.get("height", 100))
        layer = self._append_layer(
            {
                "name": f"Shape {params.get('shape_type', 'rectangle')}",
                "kind": "solid",
                "opacity": int(params.get("opacity", 100)),
                "blend_mode": "Normal",
                "visible": True,
                "color_hex": params.get("hex_color", "#FFFFFF"),
                "bounds": {
                    "left": x,
                    "top": y,
                    "right": x + w,
                    "bottom": y + h,
                    "width": w,
                    "height": h,
                    "center_x": x + w // 2,
                    "center_y": y + h // 2,
                },
            }
        )
        return {"message": f"Shape added at index {layer['index']}.", "index": layer["index"], "bounds": layer["bounds"]}

    def _op_change_shape_color(self, params: dict[str, Any]) -> dict[str, Any]:
        layer = self._layer(int(params["index"]))
        layer["color_hex"] = params.get("hex_color", "#FFFFFF")
        return {"message": f"Shape layer {params['index']} colour changed."}

    def _op_add_stroke(self, params: dict[str, Any]) -> dict[str, Any]:
        self._layer(int(params["index"]))
        return {"message": f"Stroke added to layer {params['index']}."}

    def _op_add_image_layer(self, params: dict[str, Any]) -> dict[str, Any]:
        layer = self._append_layer({"name": "Image", "kind": "normal", "opacity": int(params.get("opacity", 100)), "blend_mode": "Normal", "visible": True})
        return {"message": f"Image layer added successfully at index {layer['index']}.", "index": layer["index"]}

    def _op_add_element_layer(self, params: dict[str, Any]) -> dict[str, Any]:
        x, y = int(params.get("x", 0)), int(params.get("y", 0))
        w, h = int(params.get("width", 100)), int(params.get("height", 100))
        layer = self._append_layer(
            {
                "name": "Element",
                "kind": "normal",
                "opacity": int(params.get("opacity", 100)),
                "blend_mode": "Normal",
                "visible": True,
                "bounds": {"left": x, "top": y, "right": x + w, "bottom": y + h, "width": w, "height": h, "center_x": x + w // 2, "center_y": y + h // 2},
            }
        )
        return {"message": "Element image placed.", "index": layer["index"], "bounds": layer["bounds"]}

    def _op_add_pill_cta(self, params: dict[str, Any]) -> dict[str, Any]:
        self._op_add_shape(
            {
                "shape_type": "rectangle",
                "x": params.get("x", 0),
                "y": params.get("y", 0),
                "width": params.get("width", 200),
                "height": params.get("height", 60),
                "hex_color": params.get("pill_color", "#ff7a00"),
                "corner_radius": params.get("corner_radius", 30),
            }
        )
        self._op_add_text_layer(
            {
                "content": params.get("text", "Shop Now"),
                "x": int(params.get("x", 0)) + int(params.get("width", 200)) // 2,
                "y": int(params.get("y", 0)) + int(params.get("height", 60)) // 2,
                "font_size": params.get("font_size") or 24,
                "hex_color": params.get("text_color", "#ffffff"),
                "alignment": "center",
            }
        )
        return {"message": "PILL CTA created."}

    def _op_select_subject_and_mask(self, params: dict[str, Any]) -> dict[str, Any]:
        self._layer(int(params["index"]))
        return {"message": f"Subject selected and mask applied to layer {params['index']}."}

    def _op_generate_fill(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"message": f"Generative fill applied. Prompt: '{params.get('prompt', '')}'"}

    def _op_history_checkpoint(self, params: dict[str, Any]) -> dict[str, Any]:
        self._snapshot()
        return {"message": "History checkpoint created.", "depth": len(self._history)}

    def _op_history_undo(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self._history:
            raise PhotoshopError("No history checkpoint to restore.")
        self._doc = self._history.pop()
        return {"message": "Restored previous history checkpoint.", "depth": len(self._history)}

    def _op_execute_batchplay(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"message": "batchPlay executed (mock).", "commands": params.get("commands", [])}

    def _op_execute_jsx(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"message": "JSX executed (mock).", "script": params.get("script", "")[:80]}
