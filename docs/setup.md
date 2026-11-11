# Setup

## One command

```bash
# macOS / Linux
bash scripts/setup.sh

# Windows (cmd)
scripts\setup.bat
```

This creates `.venv`, installs dependencies, copies `.env.example` → `.env`,
creates `templates/` + `output/` + `plugins/`, and runs unit tests.

## MCP server

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
desain-mcp
# equivalent: python -m desain.mcp.server
```

Set `DESAIN_BRIDGE_BACKEND=mock` to exercise the server without Photoshop.

## Load the UXP plugin

1. Install / open **Adobe UXP Developer Tool**
2. Add Plugin → select `uxp-plugin/manifest.json`
3. Load the plugin into Photoshop
4. Open **Plugins → DES.ai.N Bridge**
5. Confirm the WebSocket URL (`ws://127.0.0.1:8765`) and click **Connect**

Order: start `desain-mcp` first, then connect the panel (the panel also
auto-reconnects).

## Configure MCP clients

### Claude Desktop

Add to the Claude Desktop MCP config (path varies by OS):

```json
{
  "mcpServers": {
    "desain": {
      "command": "/ABS/PATH/TO/DES.ai.N/.venv/bin/desain-mcp",
      "args": [],
      "env": {
        "DESAIN_BRIDGE_BACKEND": "uxp",
        "DESAIN_BRIDGE_PORT": "8765",
        "DESAIN_TEMPLATES_DIR": "/ABS/PATH/TO/DES.ai.N/templates",
        "DESAIN_OUTPUT_DIR": "/ABS/PATH/TO/DES.ai.N/output"
      }
    }
  }
}
```

### Cursor

Add a similar server entry in Cursor MCP settings, pointing `command` at the
virtualenv `desain-mcp` executable (or `python` + `-m desain.mcp.server`).

### Other MCP clients

Any client that speaks MCP stdio can launch `desain-mcp`. Streamable HTTP can be
enabled later via the MCP SDK transport option if you deploy the server as a
service.

## Windows COM fallback

```bash
set DESAIN_BRIDGE_BACKEND=com
desain-mcp
```

Requires Photoshop installed, `pywin32`, and a working COM registration. Prefer
UXP when available.

## Desktop UI (optional)

```bash
python main.py
# or double-click run.bat on Windows
```

Configure LM Studio / OpenAI-compatible endpoints through the Settings tab or
`.env` (`DESAIN_LLM_BASE_URL`, `DESAIN_LLM_API_KEY`).
