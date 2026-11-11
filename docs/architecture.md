# Architecture

DES.ai.N is a **desktop design agent** first. The UI talks to a local OpenAI-compatible
model; the agent drives Photoshop through a reliability-focused bridge layer.
MCP is an optional secondary interface for external agents.

## Runtime diagram

```
Desktop UI (PyQt)
    → Local model runtime (detect / profile / tools-or-JSON)
        → Design agent (core/ai_agent.py)
            → Photoshop backend facade
                → Bridge manager
                    ├── UXP WebSocket plugin (cross-platform)
                    ├── COM / ExtendScript (Windows)
                    └── Mock bridge (tests)
```

Optional:

```
Claude Desktop / Cursor / other MCP host
    → desain-mcp (stdio)
        → same bridge manager / Photoshop backends
```

## Local model path

1. **Detect** LM Studio (`:1234`), Ollama (`:11434`), llama.cpp (`:8080`), plus the configured base URL
2. **Profile** the loaded model id (size heuristics → temperature, context budget, tool mode)
3. **Tool strategy**
   - Capable models: native OpenAI-style tool calls
   - Small / weak tool callers: structured JSON action plans
   - Automatic fallback if native tool-calling errors
4. **Repair / retry** malformed JSON (trailing commas, fences, truncation)
5. **Self-check** against the live layer map before finalize (when enabled for the profile)

## Photoshop bridge

UXP plugins cannot bind a listening socket, so the Python process hosts a WebSocket
server and the panel connects as a client — the same pattern used by open-source
Photoshop MCP projects such as [adb-mcp](https://github.com/mikechambers/adb-mcp)
and [drmedia/photoshop-mcp](https://github.com/drmedia/photoshop-mcp).

Windows COM remains available as a fallback via `core/photoshop_client.py`.

Adobe announced local Creative Cloud MCP integrations at Adobe MAX (Nov 2026) with
private beta planned for early 2027. DES.ai.N can grow an adapter for that endpoint
when it is generally available; until then the UXP/COM bridges are the supported path.

## Reliability features

- Typed schemas for MCP / service-layer tools
- Request timeouts and structured errors
- History checkpoints before mutating operations
- UXP panel reconnect with exponential backoff
- Configuration via `.env` (see `.env.example`)

## Package layout

```
desain/local_llm/     detection, profiling, JSON tools, runtime
desain/bridge/        UXP / COM / mock transports
desain/desktop/       UI ↔ Photoshop facades
desain/mcp/           optional MCP server
core/                 desktop design agent
ui/                   PyQt shell
uxp-plugin/           Photoshop panel
```
