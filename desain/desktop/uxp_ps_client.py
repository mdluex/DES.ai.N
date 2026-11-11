"""Sync PhotoshopClient-compatible facade over the UXP WebSocket hub."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from typing import Any

from desain.bridge.uxp_bridge import UxpBridge
from desain.config import Settings

logger = logging.getLogger(__name__)


class UxpPhotoshopClient:
    def __init__(self, settings: Settings, log_callback: Callable[[str], None] | None = None) -> None:
        self.settings = settings
        self.log = log_callback or (lambda m: logger.info(m))
        self.bridge = UxpBridge(settings)
        self.app = self  # checkpoint wrapper looks for .app.DoJavaScript
        self.psd = None
        self._doc_name = None
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._started = threading.Event()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self.bridge.start())
        self._started.set()
        self._loop.run_forever()

    def connect(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()
            self._started.wait(timeout=5)
        self.log(
            f"[INFO] UXP bridge listening on ws://{self.settings.bridge_host}:{self.settings.bridge_port}. "
            "Connect the DES.ai.N Bridge panel in Photoshop."
        )

    def disconnect(self) -> None:
        if self._loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(self.bridge.stop(), self._loop)
            try:
                fut.result(timeout=5)
            except Exception:
                pass
            self._loop.call_soon_threadsafe(self._loop.stop)

    def DoJavaScript(self, script: str) -> Any:
        return self._call("execute_jsx", {"script": script})

    def _call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._started.wait(timeout=5):
            raise RuntimeError("UXP bridge failed to start.")
        fut = asyncio.run_coroutine_threadsafe(
            self.bridge.call(method, params or {}, checkpoint=False),
            self._loop,
        )
        return fut.result(timeout=self.settings.bridge_request_timeout_s)

    def create_canvas(self, width, height, filename):
        r = self._call("create_document", {"width": width, "height": height, "filename": filename})
        self.psd = object()
        self._doc_name = filename
        return r.get("message", "Canvas created.")

    def open_document(self, path):
        r = self._call("open_document", {"path": path})
        self.psd = object()
        self._doc_name = str(path)
        return r.get("message", "Document opened.")

    def close_document(self):
        r = self._call("close_document")
        self.psd = None
        return r.get("message", "Closed.")

    def save_document(self, output_folder, filename, save_psd=False):
        return self._call(
            "save_document",
            {"output_folder": output_folder, "filename": filename, "save_psd": save_psd},
        ).get("message", "Saved.")

    def export_preview(self, output_path):
        self._call("export_png", {"path": output_path})
        return True

    def get_layer_context(self):
        return self._call("get_layer_context")

    def add_text_layer(self, content, font_size, hex_color, x, y, blend_mode=1, opacity=100,
                       font_name=None, alignment="left", rotation=0, letter_spacing=None):
        return self._call(
            "add_text_layer",
            {
                "content": content,
                "font_size": font_size,
                "hex_color": hex_color,
                "x": x,
                "y": y,
                "blend_mode": blend_mode,
                "opacity": opacity,
                "font_name": font_name,
                "alignment": alignment,
                "rotation": rotation,
                "letter_spacing": letter_spacing,
            },
        ).get("message", "Text added.")

    def set_layer_properties(self, index, text=None, font_size=None, opacity=None,
                             blend_mode=None, font_name=None, hex_color=None):
        return self._call(
            "set_layer_properties",
            {
                "index": index,
                "text": text,
                "font_size": font_size,
                "opacity": opacity,
                "blend_mode": blend_mode,
                "font_name": font_name,
                "hex_color": hex_color,
            },
        ).get("message", "Updated.")

    def move_layer(self, index, delta_x, delta_y):
        return self._call("move_layer", {"index": index, "delta_x": delta_x, "delta_y": delta_y}).get("message", "Moved.")

    def rotate_layer(self, index, angle):
        return self._call("rotate_layer", {"index": index, "angle": angle}).get("message", "Rotated.")

    def scale_layer(self, index, scale_percent):
        return self._call("scale_layer", {"index": index, "scale_percent": scale_percent}).get("message", "Scaled.")

    def reorder_layer(self, index, new_index):
        return self._call("reorder_layer", {"index": index, "new_index": new_index}).get("message", "Reordered.")

    def add_solid_color_layer(self, hex_color, blend_mode=1, opacity=100):
        return self._call(
            "add_solid_color_layer",
            {"hex_color": hex_color, "blend_mode": blend_mode, "opacity": opacity},
        ).get("message", "Color added.")

    def add_gradient_layer(self, hex_color1, hex_color2, angle=90, opacity=100, blend_mode=1):
        return self._call(
            "add_gradient_layer",
            {
                "hex_color1": hex_color1,
                "hex_color2": hex_color2,
                "angle": angle,
                "opacity": opacity,
                "blend_mode": blend_mode,
            },
        ).get("message", "Gradient added.")

    def add_shape(self, shape_type, x, y, width, height, hex_color, corner_radius=0, opacity=100, rotation=0):
        return self._call(
            "add_shape",
            {
                "shape_type": shape_type,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "hex_color": hex_color,
                "corner_radius": corner_radius,
                "opacity": opacity,
                "rotation": rotation,
            },
        ).get("message", "Shape added.")

    def change_shape_color(self, index, hex_color):
        return self._call("change_shape_color", {"index": index, "hex_color": hex_color}).get("message", "Recolored.")

    def add_stroke(self, index, thickness, hex_color):
        return self._call(
            "add_stroke", {"index": index, "thickness": thickness, "hex_color": hex_color}
        ).get("message", "Stroke added.")

    def add_image_layer(self, image_path, blend_mode=1, opacity=100):
        return self._call(
            "add_image_layer", {"path": image_path, "blend_mode": blend_mode, "opacity": opacity}
        ).get("message", "Image added.")

    def add_element_layer(self, image_path, x, y, width, height, remove_bg=False,
                          blend_mode=1, opacity=100, rotation=0):
        return self._call(
            "add_element_layer",
            {
                "path": image_path,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "remove_background": remove_bg,
                "blend_mode": blend_mode,
                "opacity": opacity,
                "rotation": rotation,
            },
        ).get("message", "Element added.")

    def add_pill_cta(self, text, x, y, width, height, pill_color, text_color="#ffffff",
                     font_size=None, font_name=None, corner_radius=None):
        return self._call(
            "add_pill_cta",
            {
                "text": text,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "pill_color": pill_color,
                "text_color": text_color,
                "font_size": font_size,
                "font_name": font_name,
                "corner_radius": corner_radius,
            },
        ).get("message", "Pill CTA created.")

    def select_subject_and_mask(self, index):
        return self._call("select_subject_and_mask", {"index": index}).get("message", "Masked.")

    def generate_fill(self, prompt, x, y, width, height):
        return self._call(
            "generate_fill",
            {"prompt": prompt, "x": x, "y": y, "width": width, "height": height},
        ).get("message", "Fill applied.")
