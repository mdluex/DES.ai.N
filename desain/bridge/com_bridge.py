"""Windows COM / ExtendScript fallback bridge.

Uses the legacy ``core.photoshop_client.PhotoshopClient`` when ``pywin32`` is
available. This path remains useful until Adobe's official local MCP private
beta ships, and for environments where a UXP plugin cannot be loaded.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from desain.bridge.base import PhotoshopBridge
from desain.errors import BridgeNotConnectedError, PhotoshopError, ValidationError

logger = logging.getLogger(__name__)


class ComBridge(PhotoshopBridge):
    name = "com"

    def __init__(self, log_callback: Callable[[str], None] | None = None) -> None:
        self._log = log_callback or (lambda msg: logger.info(msg))
        self._client = None
        self._connected = False

    async def start(self) -> None:
        try:
            from core.photoshop_client import PhotoshopClient
        except Exception as exc:  # pragma: no cover - platform specific
            raise BridgeNotConnectedError(
                "COM bridge requires Windows + pywin32 + Photoshop. "
                f"Import failed: {exc}"
            ) from exc

        def _connect() -> Any:
            client = PhotoshopClient(self._log)
            client.connect()
            return client

        try:
            self._client = await asyncio.to_thread(_connect)
            self._connected = True
        except Exception as exc:  # pragma: no cover - requires Photoshop
            raise BridgeNotConnectedError(f"Failed to connect via COM: {exc}") from exc

    async def stop(self) -> None:
        if self._client is not None:
            try:
                await asyncio.to_thread(self._client.disconnect)
            except Exception:
                pass
        self._client = None
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        checkpoint: bool = False,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        if not self.is_connected():
            raise BridgeNotConnectedError("COM bridge is not connected.")
        params = params or {}

        async def _run() -> dict[str, Any]:
            if checkpoint:
                await asyncio.to_thread(self._history_checkpoint)
            return await asyncio.to_thread(self._dispatch, method, params)

        if timeout_s is None:
            return await _run()
        try:
            return await asyncio.wait_for(_run(), timeout=timeout_s)
        except asyncio.TimeoutError as exc:
            from desain.errors import BridgeTimeoutError

            raise BridgeTimeoutError(
                f"COM call '{method}' timed out.",
                details={"method": method},
            ) from exc

    def _history_checkpoint(self) -> None:
        assert self._client is not None
        js = (
            "try {"
            "  var id = stringIDToTypeID('make');"
            "  var desc = new ActionDescriptor();"
            "  var ref = new ActionReference();"
            "  ref.putClass(stringIDToTypeID('snapshotClass'));"
            "  desc.putReference(charIDToTypeID('null'), ref);"
            "  desc.putString(charIDToTypeID('Nm  '), 'DESAIN_CHECKPOINT');"
            "  desc.putEnumerated(charIDToTypeID('From'), "
            "    charIDToTypeID('HstS'), charIDToTypeID('CrnH'));"
            "  executeAction(id, desc, DialogModes.NO);"
            "} catch (e) {}"
        )
        try:
            self._client.app.DoJavaScript(js)
        except Exception as exc:
            logger.debug("History checkpoint failed: %s", exc)

    def _dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        assert self._client is not None
        c = self._client

        if method == "ping":
            return {"pong": True, "backend": "com"}
        if method == "get_status":
            return {
                "connected": True,
                "backend": "com",
                "has_document": c.psd is not None,
                "document_name": c._doc_name,
            }
        if method == "create_document":
            msg = c.create_canvas(
                int(params.get("width", 1080)),
                int(params.get("height", 1080)),
                str(params.get("filename") or params.get("name") or "Untitled"),
            )
            return {"message": msg}
        if method == "open_document":
            path = params.get("path")
            if not path:
                raise ValidationError("path is required")
            return {"message": c.open_document(path), "path": path}
        if method == "close_document":
            return {"message": c.close_document()}
        if method == "save_document":
            return {
                "message": c.save_document(
                    params.get("output_folder", "."),
                    params.get("filename", "saved_design"),
                    bool(params.get("save_psd", False)),
                )
            }
        if method == "export_png":
            ok = c.export_preview(params.get("path"))
            if not ok:
                raise PhotoshopError("Export failed.")
            return {"message": "Preview exported.", "path": params.get("path")}
        if method == "get_layer_context":
            return c.get_layer_context()
        if method == "add_text_layer":
            return {
                "message": c.add_text_layer(
                    params.get("content", "Text"),
                    int(params.get("font_size", 72)),
                    params.get("hex_color", "#FFFFFF"),
                    int(params.get("x", 100)),
                    int(params.get("y", 200)),
                    int(params.get("blend_mode", 1)),
                    int(params.get("opacity", 100)),
                    params.get("font_name"),
                    params.get("alignment", "left"),
                    float(params.get("rotation", 0) or 0),
                    params.get("letter_spacing"),
                )
            }
        if method == "set_layer_properties":
            return {
                "message": c.set_layer_properties(
                    int(params["index"]),
                    params.get("text"),
                    params.get("font_size"),
                    params.get("opacity"),
                    params.get("blend_mode"),
                    params.get("font_name"),
                    params.get("hex_color"),
                )
            }
        if method == "move_layer":
            return {
                "message": c.move_layer(
                    int(params["index"]),
                    int(params.get("delta_x", 0)),
                    int(params.get("delta_y", 0)),
                )
            }
        if method == "rotate_layer":
            return {"message": c.rotate_layer(int(params["index"]), float(params.get("angle", 0)))}
        if method == "scale_layer":
            return {
                "message": c.scale_layer(
                    int(params["index"]),
                    float(params.get("scale_percent", 100)),
                )
            }
        if method == "reorder_layer":
            return {
                "message": c.reorder_layer(int(params["index"]), int(params["new_index"]))
            }
        if method == "add_solid_color_layer":
            return {
                "message": c.add_solid_color_layer(
                    params.get("hex_color", "#000000"),
                    int(params.get("blend_mode", 1)),
                    int(params.get("opacity", 100)),
                )
            }
        if method == "add_gradient_layer":
            return {
                "message": c.add_gradient_layer(
                    params.get("hex_color1", "#000000"),
                    params.get("hex_color2", "#333333"),
                    int(params.get("angle", 90)),
                    int(params.get("opacity", 100)),
                    int(params.get("blend_mode", 1)),
                )
            }
        if method == "add_shape":
            return {
                "message": c.add_shape(
                    params.get("shape_type", "rectangle"),
                    int(params.get("x", 0)),
                    int(params.get("y", 0)),
                    int(params.get("width", 100)),
                    int(params.get("height", 100)),
                    params.get("hex_color", "#FFFFFF"),
                    int(params.get("corner_radius", 0) or 0),
                    int(params.get("opacity", 100)),
                    float(params.get("rotation", 0) or 0),
                )
            }
        if method == "change_shape_color":
            return {
                "message": c.change_shape_color(
                    int(params["index"]), params.get("hex_color", "#FFFFFF")
                )
            }
        if method == "add_stroke":
            return {
                "message": c.add_stroke(
                    int(params["index"]),
                    int(params.get("thickness", 2)),
                    params.get("hex_color", "#FFFFFF"),
                )
            }
        if method == "add_image_layer":
            return {
                "message": c.add_image_layer(
                    params["path"],
                    int(params.get("blend_mode", 1)),
                    int(params.get("opacity", 100)),
                )
            }
        if method == "add_element_layer":
            return {
                "message": c.add_element_layer(
                    params["path"],
                    int(params.get("x", 0)),
                    int(params.get("y", 0)),
                    int(params.get("width", 400)),
                    int(params.get("height", 400)),
                    bool(params.get("remove_background", False)),
                    int(params.get("blend_mode", 1)),
                    int(params.get("opacity", 100)),
                    float(params.get("rotation", 0) or 0),
                )
            }
        if method == "add_pill_cta":
            return {
                "message": c.add_pill_cta(
                    params.get("text", "Shop Now"),
                    int(params.get("x", 100)),
                    int(params.get("y", 100)),
                    int(params.get("width", 400)),
                    int(params.get("height", 120)),
                    params.get("pill_color", "#ff7a00"),
                    params.get("text_color", "#ffffff"),
                    params.get("font_size"),
                    params.get("font_name"),
                    params.get("corner_radius"),
                )
            }
        if method == "select_subject_and_mask":
            return {"message": c.select_subject_and_mask(int(params["index"]))}
        if method == "generate_fill":
            return {
                "message": c.generate_fill(
                    params.get("prompt", ""),
                    int(params.get("x", 0)),
                    int(params.get("y", 0)),
                    int(params.get("width", 500)),
                    int(params.get("height", 500)),
                )
            }
        if method == "history_checkpoint":
            self._history_checkpoint()
            return {"message": "History checkpoint created."}
        if method == "history_undo":
            try:
                c.app.DoJavaScript("executeAction(charIDToTypeID('undo'), undefined, DialogModes.NO);")
            except Exception as exc:
                raise PhotoshopError(f"Undo failed: {exc}") from exc
            return {"message": "Undo executed."}
        if method == "execute_jsx":
            script = params.get("script", "")
            result = c.app.DoJavaScript(script)
            return {"message": "JSX executed.", "result": result}
        if method == "execute_batchplay":
            # COM fallback: wrap batchPlay descriptors is not available; use JSX bridge.
            raise ValidationError(
                "execute_batchplay is only available on the UXP bridge. Use execute_jsx on COM."
            )

        raise ValidationError(f"Unsupported COM method: {method}")
