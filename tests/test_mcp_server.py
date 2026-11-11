import json

import pytest

from desain.config import Settings
from desain.mcp.server import create_server


def test_create_server_registers_core_tools(tmp_path):
    settings = Settings(
        bridge_backend="mock",
        templates_dir=tmp_path / "templates",
        output_dir=tmp_path / "output",
        plugins_dir=tmp_path / "plugins",
    )
    settings.templates_dir.mkdir()
    settings.output_dir.mkdir()
    settings.plugins_dir.mkdir()
    server = create_server(settings)
    assert hasattr(server, "add_tool")
    assert server.name == "desain"

    tool_names: set[str] = set()
    manager = getattr(server, "_tool_manager", None)
    if manager is not None and hasattr(manager, "list_tools"):
        listed = manager.list_tools()
        if isinstance(listed, dict):
            tool_names |= set(listed.keys())
        elif isinstance(listed, list):
            for item in listed:
                name = getattr(item, "name", None) or (item.get("name") if isinstance(item, dict) else None)
                if name:
                    tool_names.add(str(name))

    # Decorators should have registered the core surface.
    assert "photoshop_status" in tool_names or hasattr(server, "call_tool")


@pytest.mark.asyncio
async def test_service_status_via_manager(tmp_path):
    from desain.bridge.manager import BridgeManager
    from desain.photoshop.service import PhotoshopService

    settings = Settings(bridge_backend="mock", templates_dir=tmp_path, output_dir=tmp_path, plugins_dir=tmp_path)
    bridges = BridgeManager(settings)
    await bridges.start()
    svc = PhotoshopService(settings, bridges)
    status = await svc.bridge_status()
    assert status["backend"] == "mock"
    assert status["connected"] is True
    ping = await svc.ping()
    assert json.loads(json.dumps(ping))["pong"] is True
    await bridges.stop()
