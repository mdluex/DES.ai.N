"""Simple plugin loader for custom MCP tools without forking the agent.

A plugin is a Python module under ``plugins/`` that exports:

    PLUGIN = {
        "name": "example",
        "tools": [
            {
                "name": "example_echo",
                "description": "Echo a message",
                "handler": callable,  # async or sync (dict -> dict/str)
                "input_schema": {...},  # optional JSON Schema
            }
        ],
    }
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., Any | Awaitable[Any]]


class PluginTool:
    def __init__(
        self,
        name: str,
        description: str,
        handler: ToolHandler,
        input_schema: dict[str, Any] | None = None,
        plugin_name: str = "unknown",
    ) -> None:
        self.name = name
        self.description = description
        self.handler = handler
        self.input_schema = input_schema or {
            "type": "object",
            "properties": {},
            "additionalProperties": True,
        }
        self.plugin_name = plugin_name


def load_plugins(plugins_dir: Path) -> list[PluginTool]:
    tools: list[PluginTool] = []
    if not plugins_dir.exists():
        return tools

    for path in sorted(plugins_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = f"desain_user_plugin_{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            plugin = getattr(module, "PLUGIN", None)
            if not isinstance(plugin, dict):
                logger.warning("Plugin %s missing PLUGIN dict", path.name)
                continue
            plugin_name = str(plugin.get("name") or path.stem)
            for entry in plugin.get("tools") or []:
                tool = PluginTool(
                    name=str(entry["name"]),
                    description=str(entry.get("description") or entry["name"]),
                    handler=entry["handler"],
                    input_schema=entry.get("input_schema"),
                    plugin_name=plugin_name,
                )
                tools.append(tool)
                logger.info("Loaded plugin tool %s from %s", tool.name, plugin_name)
        except Exception as exc:
            logger.exception("Failed to load plugin %s: %s", path, exc)
    return tools
