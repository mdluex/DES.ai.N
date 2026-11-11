# Setup

## One command

```bash
# macOS / Linux
bash scripts/setup.sh

# Windows (cmd)
scripts\setup.bat
```

Creates `.venv`, installs dependencies, copies `.env.example` → `.env`, creates
`templates/` + `output/` + `plugins/`, and runs unit tests.

## Desktop app (primary)

1. Start a local model server (LM Studio recommended).
2. Activate the venv and launch:

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python main.py
```

On Windows you can also double-click `run.bat`.

3. Connect Photoshop:

### Windows COM (default on Windows)

Install Photoshop with scripting/COM support. The app connects via
`Photoshop.Application`.

### UXP bridge (macOS and cross-platform)

1. Start the desktop app (it listens for the bridge when `DESAIN_BRIDGE_BACKEND=uxp` or non-Windows `auto`).
2. Open Adobe UXP Developer Tool → Add Plugin → `uxp-plugin/manifest.json` → Load.
3. In Photoshop: **Plugins → DES.ai.N Bridge** → confirm `ws://127.0.0.1:8765` → Connect.

4. Place templates in `templates/`, set folders in Settings if needed, then chat in **AI Workspace**.

### Local model settings

| Setting | Default |
|---|---|
| Provider | `local` (auto-detect) |
| Base URL | `http://127.0.0.1:1234/v1` |
| API key | optional for most local servers |

Override with `.env` or the Settings tab.

## Optional MCP integration

Use this only if you want Claude Desktop, Cursor, or another MCP client to call
DES.ai.N tools directly.

```bash
desain-mcp
# equivalent: python -m desain.mcp.server
```

Example Claude Desktop snippet:

```json
{
  "mcpServers": {
    "desain": {
      "command": "/ABS/PATH/TO/DES.ai.N/.venv/bin/desain-mcp",
      "args": [],
      "env": {
        "DESAIN_BRIDGE_BACKEND": "uxp",
        "DESAIN_BRIDGE_PORT": "8765"
      }
    }
  }
}
```

Load the UXP panel (or set `DESAIN_BRIDGE_BACKEND=com` on Windows) before issuing tool calls.
Tool list: [tools.md](tools.md).
