"""Photoshop backend selection for the desktop UI."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from typing import Any

from desain.config import Settings

logger = logging.getLogger(__name__)


class CheckpointingClient:
    """Wrap a Photoshop client and create history checkpoints before mutations."""

    _MUTATING = frozenset(
        {
            "create_canvas",
            "open_document",
            "close_document",
            "add_text_layer",
            "set_layer_properties",
            "move_layer",
            "rotate_layer",
            "scale_layer",
            "reorder_layer",
            "add_solid_color_layer",
            "add_gradient_layer",
            "add_shape",
            "change_shape_color",
            "add_stroke",
            "add_image_layer",
            "add_element_layer",
            "add_pill_cta",
            "select_subject_and_mask",
            "generate_fill",
        }
    )

    def __init__(self, inner: Any, *, enabled: bool = True, log: Callable[[str], None] | None = None):
        self._inner = inner
        self._enabled = enabled
        self._log = log or (lambda _m: None)

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._inner, name)
        if not callable(attr) or name not in self._MUTATING or not self._enabled:
            return attr

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self._checkpoint()
            return attr(*args, **kwargs)

        return wrapper

    def _checkpoint(self) -> None:
        try:
            app = getattr(self._inner, "app", None)
            if app is None:
                return
            js = (
                "try {"
                "  var desc = new ActionDescriptor();"
                "  var ref = new ActionReference();"
                "  ref.putClass(stringIDToTypeID('snapshotClass'));"
                "  desc.putReference(charIDToTypeID('null'), ref);"
                "  desc.putString(charIDToTypeID('Nm  '), 'DESAIN_CHECKPOINT');"
                "  desc.putEnumerated(charIDToTypeID('From'), "
                "    charIDToTypeID('HstS'), charIDToTypeID('CrnH'));"
                "  executeAction(stringIDToTypeID('make'), desc, DialogModes.NO);"
                "} catch (e) {}"
            )
            app.DoJavaScript(js)
        except Exception as exc:
            self._log(f"[INFO] History checkpoint skipped: {exc}")

    @property
    def psd(self) -> Any:
        return getattr(self._inner, "psd", None)

    @psd.setter
    def psd(self, value: Any) -> None:
        self._inner.psd = value


def create_photoshop_backend(
    settings: Settings,
    log_callback: Callable[[str], None] | None = None,
) -> Any:
    """Create the desktop Photoshop client.

    Preference order:
    1. Explicit ``com`` / Windows auto → COM ``PhotoshopClient``
    2. Explicit ``uxp`` → requires the UXP bridge plugin (sync helper)
    3. ``mock`` → in-process mock for development without Photoshop
    """
    log = log_callback or (lambda m: logger.info(m))
    backend = settings.bridge_backend

    if backend == "mock":
        from desain.bridge.mock_bridge import MockBridge
        from desain.desktop.mock_ps_client import MockPhotoshopClient

        log("[INFO] Using mock Photoshop backend.")
        return CheckpointingClient(MockPhotoshopClient(MockBridge()), enabled=False, log=log)

    if backend == "uxp":
        from desain.desktop.uxp_ps_client import UxpPhotoshopClient

        log("[INFO] Using UXP WebSocket Photoshop backend.")
        client = UxpPhotoshopClient(settings, log_callback=log)
        client.connect()
        return CheckpointingClient(client, enabled=settings.history_checkpoint, log=log)

    # auto / com
    if sys.platform.startswith("win") or backend == "com":
        from core.photoshop_client import PhotoshopClient

        log("[INFO] Using Photoshop COM backend.")
        client = PhotoshopClient(log)
        client.connect()
        return CheckpointingClient(client, enabled=settings.history_checkpoint, log=log)

    # Non-Windows auto: prefer UXP
    from desain.desktop.uxp_ps_client import UxpPhotoshopClient

    log("[INFO] Non-Windows platform — using UXP WebSocket Photoshop backend.")
    client = UxpPhotoshopClient(settings, log_callback=log)
    client.connect()
    return CheckpointingClient(client, enabled=settings.history_checkpoint, log=log)
