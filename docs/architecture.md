# Architecture

## Decision summary (late 2026)

DES.ai.N uses **Model Context Protocol (MCP)** as the agent interface and a
**Photoshop UXP plugin over WebSocket** as the primary execution bridge, with a
**Windows COM / ExtendScript fallback**.

### Why this shape

| Candidate | Status in late 2026 | Role in DES.ai.N |
|---|---|---|
| **Adobe official local MCP for Creative Cloud** | Announced / previewed at Adobe MAX (10 Nov 2026); private beta targeted for early 2027 | Tracked as the preferred long-term path once generally available. Not used as the runtime dependency yet. |
| **MCP + UXP WebSocket bridge** | De-facto open-source standard for agent control of Photoshop | **Primary architecture** |
| **ExtendScript / COM / batchPlay** | Mature, Windows-strong, still useful | **Fallback** for hosts that cannot load UXP |
| **Open-source Photoshop MCP servers** | Multiple public references (see below) | Inform protocol and reliability patterns |

### Sources

1. Adobe Newsroom — *Adobe Transforms its Creative Cloud Tools into Agentic Workflows…* (10 Nov 2026): local MCP integrations previewed for Photoshop, Illustrator, Premiere, After Effects; private beta early 2027.  
   https://news.adobe.com/news/2026/11/adobe-transforms-creative-cloud-tools
2. TechCrunch coverage of Adobe MAX MCP announcement (10 Nov 2026).  
   https://techcrunch.com/2026/11/10/adobe-adds-more-ai-to-its-products-and-launches-an-mcp/
3. Model Context Protocol — industry standard agent tool interface (MCP Python SDK v2).  
   https://modelcontextprotocol.io / https://github.com/modelcontextprotocol/python-sdk
4. Open-source precedents for UXP-as-WebSocket-client (UXP cannot bind a listening socket):
   - [mikechambers/adb-mcp](https://github.com/mikechambers/adb-mcp)
   - [drmedia/photoshop-mcp](https://github.com/drmedia/photoshop-mcp)
   - [CORE-Automate-WSS/photoshop-mcp](https://github.com/CORE-Automate-WSS/photoshop-mcp)
   - [StarBoze/Photoshop-MCP-Server](https://github.com/StarBoze/Photoshop-MCP-Server)
   - [loonghao/dcc-mcp-photoshop](https://github.com/loonghao/dcc-mcp-photoshop) (adobepy broker variant)

## Runtime diagram

```
MCP Client (Claude Desktop, Cursor, …)
        │  MCP stdio (or streamable HTTP later)
        ▼
DES.ai.N MCP Server  (Python, package: desain)
        │  validated tool calls + timeouts + logging
        ▼
Bridge Manager
   ├── UXP WebSocket Hub  ──ws://127.0.0.1:8765──►  UXP plugin in Photoshop
   │                                                 (DOM + batchPlay)
   ├── COM Bridge (Windows) ──────────────────────►  Photoshop.Application
   │                                                 (DoJavaScript / COM)
   └── Mock Bridge ───────────────────────────────►  in-memory document
                                                     (unit tests / CI)
```

## Reliability features

- **Typed tool schemas** (Pydantic) with hex/range validation before any Photoshop call
- **Request timeouts** (`DESAIN_BRIDGE_TIMEOUT_S`)
- **History checkpoints** before mutating operations when enabled
- **UXP reconnect** with exponential backoff inside the panel
- **Structured errors** (`code`, `message`, `retryable`) returned to MCP clients as JSON
- **Secrets via `.env`** — no API keys in source
- **Plugin directory** for custom tools without forking the server

## Package layout

```
desain/
  config.py              # env-based settings
  logging_setup.py
  errors.py
  bridge/                # transports
  photoshop/             # schemas + service layer
  mcp/server.py          # MCP tool surface
  plugins/loader.py
uxp-plugin/              # Adobe UXP panel (WebSocket client)
core/                    # legacy DesignAgent + COM client (UI path)
ui/                      # optional PyQt desktop shell
plugins/                 # user-authored MCP tool plugins
tests/                   # unit tests + mocked bridge
```

## Relationship to the desktop UI

The PyQt “AI Graphic Designer” shell remains available (`python main.py`) and
continues to drive Photoshop through the legacy COM client on Windows. The MCP
server is the supported integration path for Claude Desktop, Cursor, and other
MCP hosts. Both paths share template helpers and configuration conventions.
