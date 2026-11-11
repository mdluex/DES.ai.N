"""MCP server exposing Photoshop tools to Claude Desktop, Cursor, and other clients."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp.server import MCPServer
from pydantic import BaseModel, Field

from desain.bridge.manager import BridgeManager
from desain.config import Settings, get_settings
from desain.errors import DesainError
from desain.logging_setup import configure_logging, get_logger
from desain.photoshop.service import PhotoshopService
from desain.plugins.loader import PluginTool, load_plugins

logger = get_logger(__name__)


class AppContext(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    settings: Settings
    bridges: BridgeManager
    service: PhotoshopService
    plugin_tools: list[PluginTool] = Field(default_factory=list)


def _format_tool_result(data: Any) -> str:
    if isinstance(data, str):
        return data
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _format_error(exc: Exception) -> str:
    if isinstance(exc, DesainError):
        return json.dumps({"ok": False, "error": exc.to_dict()}, ensure_ascii=False, indent=2)
    return json.dumps(
        {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": str(exc)}},
        ensure_ascii=False,
        indent=2,
    )


def create_server(settings: Settings | None = None) -> MCPServer:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)

    bridges = BridgeManager(settings)
    service = PhotoshopService(settings, bridges)
    plugin_tools = load_plugins(settings.plugins_dir)

    @asynccontextmanager
    async def lifespan(server: MCPServer) -> AsyncIterator[AppContext]:
        await bridges.start()
        logger.info(
            "DES.ai.N MCP server ready (backend=%s, bridge=ws://%s:%s)",
            settings.bridge_backend,
            settings.bridge_host,
            settings.bridge_port,
        )
        try:
            yield AppContext(
                settings=settings,
                bridges=bridges,
                service=service,
                plugin_tools=plugin_tools,
            )
        finally:
            await bridges.stop()

    mcp = MCPServer(
        "desain",
        instructions=(
            "DES.ai.N controls Adobe Photoshop for design automation. "
            "Prefer inspecting layer context before edits. Mutating tools create "
            "history checkpoints when enabled. Use list_templates / open_template "
            "for PSD/PSB libraries, or create_canvas for new work."
        ),
        lifespan=lifespan,
    )

    def _svc() -> PhotoshopService:
        # Lifespan context is attached by the SDK during serving; for direct
        # unit tests we fall back to the closure-bound service.
        return service

    @mcp.tool(name="photoshop_status")
    async def photoshop_status() -> str:
        """Return bridge and Photoshop connection status."""
        try:
            return _format_tool_result(await _svc().bridge_status())
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="list_templates")
    async def list_templates() -> str:
        """List available .psd/.psb templates in the configured templates directory."""
        try:
            return _format_tool_result(await _svc().list_templates())
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="open_template")
    async def open_template(filename: str) -> str:
        """Open a PSD/PSB template from the templates library and return layer context."""
        try:
            return _format_tool_result(await _svc().open_template(filename=filename))
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="create_canvas")
    async def create_canvas(width: int, height: int, filename: str) -> str:
        """Create a new blank Photoshop document."""
        try:
            return _format_tool_result(
                await _svc().create_canvas(width=width, height=height, filename=filename)
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="get_layer_context")
    async def get_layer_context() -> str:
        """Return canvas size, fonts, and a detailed layer map for the active document."""
        try:
            return _format_tool_result(await _svc().get_layer_context())
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="add_text_layer")
    async def add_text_layer(
        content: str,
        font_size: int,
        hex_color: str,
        x: int,
        y: int,
        alignment: str = "left",
        opacity: int = 100,
        font_name: str | None = None,
        rotation: float = 0,
        letter_spacing: float | None = None,
        blend_mode: int = 1,
    ) -> str:
        """Add a text layer. y is the text baseline."""
        try:
            return _format_tool_result(
                await _svc().add_text_layer(
                    content=content,
                    font_size=font_size,
                    hex_color=hex_color,
                    x=x,
                    y=y,
                    alignment=alignment,
                    opacity=opacity,
                    font_name=font_name,
                    rotation=rotation,
                    letter_spacing=letter_spacing,
                    blend_mode=blend_mode,
                )
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="set_layer_properties")
    async def set_layer_properties(
        index: int,
        text: str | None = None,
        font_size: int | None = None,
        font_name: str | None = None,
        hex_color: str | None = None,
        opacity: int | None = None,
        blend_mode: int | None = None,
    ) -> str:
        """Modify an existing layer's text, font, color, size, opacity, or blend mode."""
        try:
            return _format_tool_result(
                await _svc().set_layer_properties(
                    index=index,
                    text=text,
                    font_size=font_size,
                    font_name=font_name,
                    hex_color=hex_color,
                    opacity=opacity,
                    blend_mode=blend_mode,
                )
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="move_layer")
    async def move_layer(index: int, delta_x: int, delta_y: int) -> str:
        """Translate a layer by pixel offsets."""
        try:
            return _format_tool_result(
                await _svc().move_layer(index=index, delta_x=delta_x, delta_y=delta_y)
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="rotate_layer")
    async def rotate_layer(index: int, angle: float) -> str:
        """Rotate a layer around its center (degrees, positive = clockwise)."""
        try:
            return _format_tool_result(await _svc().rotate_layer(index=index, angle=angle))
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="scale_layer")
    async def scale_layer(index: int, scale_percent: float) -> str:
        """Uniformly scale a layer by percentage (100 = unchanged)."""
        try:
            return _format_tool_result(
                await _svc().scale_layer(index=index, scale_percent=scale_percent)
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="reorder_layer")
    async def reorder_layer(index: int, new_index: int) -> str:
        """Move a layer to a different position in the layer stack."""
        try:
            return _format_tool_result(
                await _svc().reorder_layer(index=index, new_index=new_index)
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="add_solid_color_layer")
    async def add_solid_color_layer(
        hex_color: str, blend_mode: int = 1, opacity: int = 100
    ) -> str:
        """Add a solid color fill layer."""
        try:
            return _format_tool_result(
                await _svc().add_solid_color_layer(
                    hex_color=hex_color, blend_mode=blend_mode, opacity=opacity
                )
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="add_gradient_layer")
    async def add_gradient_layer(
        hex_color1: str,
        hex_color2: str,
        angle: int = 90,
        blend_mode: int = 1,
        opacity: int = 100,
    ) -> str:
        """Add a two-color linear gradient layer."""
        try:
            return _format_tool_result(
                await _svc().add_gradient_layer(
                    hex_color1=hex_color1,
                    hex_color2=hex_color2,
                    angle=angle,
                    blend_mode=blend_mode,
                    opacity=opacity,
                )
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="add_shape")
    async def add_shape(
        shape_type: str,
        x: int,
        y: int,
        width: int,
        height: int,
        hex_color: str,
        corner_radius: int = 0,
        opacity: int = 100,
        rotation: float = 0,
    ) -> str:
        """Add a vector rectangle, ellipse, or circle."""
        try:
            return _format_tool_result(
                await _svc().add_shape(
                    shape_type=shape_type,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    hex_color=hex_color,
                    corner_radius=corner_radius,
                    opacity=opacity,
                    rotation=rotation,
                )
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="change_shape_color")
    async def change_shape_color(index: int, hex_color: str) -> str:
        """Change the fill color of an existing shape layer."""
        try:
            return _format_tool_result(
                await _svc().change_shape_color(index=index, hex_color=hex_color)
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="add_stroke")
    async def add_stroke(index: int, thickness: int, hex_color: str) -> str:
        """Add an outline stroke style to a layer."""
        try:
            return _format_tool_result(
                await _svc().add_stroke(index=index, thickness=thickness, hex_color=hex_color)
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="add_image_layer")
    async def add_image_layer(
        keyword: str,
        blend_mode: int = 1,
        opacity: int = 100,
        path: str | None = None,
    ) -> str:
        """Place a full-canvas background image from Unsplash (or a local path)."""
        try:
            return _format_tool_result(
                await _svc().add_image_layer(
                    keyword=keyword, blend_mode=blend_mode, opacity=opacity, path=path
                )
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="add_element_layer")
    async def add_element_layer(
        keyword: str,
        x: int,
        y: int,
        width: int,
        height: int,
        remove_background: bool = False,
        blend_mode: int = 1,
        opacity: int = 100,
        rotation: float = 0,
        path: str | None = None,
    ) -> str:
        """Place a positioned image element (optional Select Subject mask)."""
        try:
            return _format_tool_result(
                await _svc().add_element_layer(
                    keyword=keyword,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    remove_background=remove_background,
                    blend_mode=blend_mode,
                    opacity=opacity,
                    rotation=rotation,
                    path=path,
                )
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="add_pill_cta")
    async def add_pill_cta(
        text: str,
        x: int,
        y: int,
        width: int,
        height: int,
        pill_color: str,
        text_color: str = "#FFFFFF",
        font_size: int | None = None,
        font_name: str | None = None,
        corner_radius: int | None = None,
    ) -> str:
        """Create a rounded CTA pill with centered text in one step."""
        try:
            return _format_tool_result(
                await _svc().add_pill_cta(
                    text=text,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    pill_color=pill_color,
                    text_color=text_color,
                    font_size=font_size,
                    font_name=font_name,
                    corner_radius=corner_radius,
                )
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="select_subject_and_mask")
    async def select_subject_and_mask(index: int) -> str:
        """Run Photoshop Select Subject and apply a layer mask."""
        try:
            return _format_tool_result(await _svc().select_subject_and_mask(index=index))
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="generate_fill")
    async def generate_fill(prompt: str, x: int, y: int, width: int, height: int) -> str:
        """Run Generative Fill in a rectangular selection (Photoshop 2024+ / Firefly)."""
        try:
            return _format_tool_result(
                await _svc().generate_fill(
                    prompt=prompt, x=x, y=y, width=width, height=height
                )
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="save_document")
    async def save_document(filename: str, save_psd: bool = False) -> str:
        """Export PNG (and optional PSD/PSB) without closing the document."""
        try:
            return _format_tool_result(
                await _svc().save_document(filename=filename, save_psd=save_psd)
            )
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="close_document")
    async def close_document() -> str:
        """Close the active document without saving."""
        try:
            return _format_tool_result(await _svc().close_document())
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="history_checkpoint")
    async def history_checkpoint() -> str:
        """Create an explicit Photoshop history snapshot / undo checkpoint."""
        try:
            return _format_tool_result(await _svc().history_checkpoint())
        except Exception as exc:
            return _format_error(exc)

    @mcp.tool(name="history_undo")
    async def history_undo(steps: int = 1) -> str:
        """Undo one or more history steps."""
        try:
            return _format_tool_result(await _svc().history_undo(steps=steps))
        except Exception as exc:
            return _format_error(exc)

    # Register plugin tools dynamically.
    for plugin_tool in plugin_tools:
        _register_plugin_tool(mcp, plugin_tool)

    return mcp


def _register_plugin_tool(mcp: MCPServer, plugin_tool: PluginTool) -> None:
    async def _handler(**kwargs: Any) -> str:
        try:
            result = plugin_tool.handler(**kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return _format_tool_result(result)
        except Exception as exc:
            return _format_error(exc)

    _handler.__name__ = plugin_tool.name
    _handler.__doc__ = plugin_tool.description
    mcp.add_tool(_handler, name=plugin_tool.name, description=plugin_tool.description)


def main() -> None:
    settings = get_settings()
    server = create_server(settings)
    server.run()


if __name__ == "__main__":
    main()
