<p align="center">
  <img src="logo.png" alt="DES.ai.N Logo" width="800"/>
</p>

<h1 align="center">DES.ai.N — AI Graphic Designer for Photoshop</h1>

<p align="center">
  A desktop app that chats with a <b>local</b> AI model and builds designs inside Adobe Photoshop.<br/>
  Built for LM Studio, Ollama, llama.cpp, and other OpenAI-compatible local servers.
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python"></a>
  <a href="https://www.adobe.com/products/photoshop.html"><img src="https://img.shields.io/badge/Adobe-Photoshop-31A8FF?logo=adobephotoshop" alt="Photoshop"></a>
  <a href="https://lmstudio.ai/"><img src="https://img.shields.io/badge/LLM-Local%20%2F%20Offline-8B5CF6" alt="Local LLM"></a>
  <a href="https://github.com/mdluex/DES.ai.N/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Source%20Available%20%7C%20Non--Commercial-orange.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/status-active%20development-success" alt="Status: Active">
</p>

---

## What it is

DES.ai.N is a standalone desktop tool. You talk to its built-in agent in the app
UI; the agent opens templates, edits layers, places imagery, runs quality checks,
and exports finished designs in Photoshop.

The product focus is **local / offline models**:

- Auto-detects LM Studio, Ollama, and llama.cpp OpenAI-compatible endpoints
- Model-aware prompting and tool strategies for small models
- Structured JSON action plans with validation, repair, and retry when native tool-calling is weak or missing
- Sensible defaults by model size, context trimming, step planning, and document self-check
- Cloud LLMs are optional and never the default

Photoshop control uses a reliable bridge layer: **UXP WebSocket plugin** (cross-platform)
with a **Windows COM fallback**, history checkpoints, timeouts, and typed validation.

---

## Demo

<p align="center">
  <video src="https://github.com/mdluex/DES.ai.N/raw/main/explainer.mp4" controls muted playsinline width="720">
    Your browser doesn't support embedded video.
    <a href="explainer.mp4">Download the explainer video</a>
  </video>
</p>

---

## Features

| Feature | Description |
|---|---|
| **Chat-first desktop UI** | Prompt the agent from the built-in workspace |
| **Local model runtime** | LM Studio / Ollama / llama.cpp auto-detection and profiling |
| **Template intelligence** | Open matching `.psd` / `.psb` templates from your library |
| **Vision analysis + QA** | Template breakdown and multi-round visual QA before export |
| **Design tools** | Text, shapes, gradients, strokes, CTAs, imagery, Select Subject, Generative Fill |
| **Reliable Photoshop bridge** | UXP WebSocket + COM fallback, checkpoints, structured errors |
| **Live preview** | Watch the design update while the agent works |

---

## Requirements

- Python 3.10+
- Adobe Photoshop (UXP plugin path, or Windows COM scripting)
- A local OpenAI-compatible model server (LM Studio recommended; Ollama and llama.cpp supported)
- A vision-capable model is recommended for template analysis and QA

---

## One-command install

```bash
# macOS / Linux
bash scripts/setup.sh

# Windows
scripts\setup.bat
```

This creates `.venv`, installs dependencies, writes `.env` from `.env.example`,
creates `templates/` + `output/`, and runs unit tests.

---

## Quick start (desktop UI)

1. Start your local model server (LM Studio on `http://127.0.0.1:1234/v1` is the default).
2. Launch the app:

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python main.py
# Windows shortcut: run.bat
```

3. Connect Photoshop:
   - **Windows (default):** COM scripting — Photoshop should be installed and launchable.
   - **UXP (macOS / preferred cross-platform):** load `uxp-plugin/` in Adobe UXP Developer Tool, open **Plugins → DES.ai.N Bridge**, connect to `ws://127.0.0.1:8765`.
4. Drop `.psd` / `.psb` files into `templates/`.
5. In **Settings**, confirm the local base URL (or leave defaults for auto-detect).
6. In **AI Workspace**, prompt:

```
Create a luxury watch ad with gold and black theme
```

```
Open the ego template and change the headline to "Ride the Future"
```

More detail: [docs/setup.md](docs/setup.md)

---

## Offline / local models

DES.ai.N treats local inference as the primary path.

| Server | Typical URL | Notes |
|---|---|---|
| **LM Studio** | `http://127.0.0.1:1234/v1` | Default; enable the local server |
| **Ollama** | `http://127.0.0.1:11434/v1` | OpenAI-compatible endpoint |
| **llama.cpp** | `http://127.0.0.1:8080/v1` | Common default port |

Set `DESAIN_LLM_PROVIDER=local` (default) to auto-detect. Model size heuristics
adjust temperature, context window, few-shot examples, and whether to use native
tool calls or JSON action plans.

Cloud providers (`openai`, `groq`, …) can be selected explicitly in `.env` when needed.

---

## Use DES.ai.N from your own agent (optional)

In addition to the desktop app, DES.ai.N can expose Photoshop tools over
**Model Context Protocol (MCP)** for Claude Desktop, Cursor, and other MCP clients.

```bash
desain-mcp
# or: python -m desain.mcp.server
```

Point your MCP host at the `desain-mcp` executable in the virtualenv, load the
UXP bridge panel (or use the COM backend on Windows), then call the published
tools. See [docs/setup.md](docs/setup.md#optional-mcp-integration) and
[docs/tools.md](docs/tools.md).

This path is optional. The primary product experience is the desktop UI.

---

## Architecture

```
Desktop UI  →  Local model runtime  →  Design agent
                                         ↓
                                   Bridge manager
                          ┌──────────┼──────────┐
                       UXP WS      COM        Mock
                    (Photoshop)  (Windows)   (tests)
```

Write-up and references: [docs/architecture.md](docs/architecture.md)

---

## Configuration

Copy `.env.example` → `.env` (setup scripts do this).

| Variable | Purpose |
|---|---|
| `DESAIN_LLM_PROVIDER` | `local` (default), `lmstudio`, `ollama`, `llamacpp`, or a cloud id |
| `DESAIN_LLM_BASE_URL` | Preferred OpenAI-compatible base URL |
| `DESAIN_LLM_AUTO_DETECT` | Probe common local ports |
| `DESAIN_BRIDGE_BACKEND` | `auto` / `uxp` / `com` / `mock` |
| `DESAIN_BRIDGE_PORT` | UXP WebSocket port (default `8765`) |
| `DESAIN_TEMPLATES_DIR` / `DESAIN_OUTPUT_DIR` | Paths |
| `UNSPLASH_ACCESS_KEY` | Optional stock imagery |

---

## Project structure

```
main.py / ui/           Desktop application
core/                   Design agent (prompts, vision QA, tool dispatch)
desain/
  local_llm/            Local model detect / profile / JSON tools / runtime
  bridge/               UXP, COM, mock Photoshop bridges
  desktop/              UI ↔ bridge adapters
  mcp/                  Optional MCP server
uxp-plugin/             Photoshop UXP bridge panel
templates/  output/     User content folders
docs/                   Setup, architecture, tools, troubleshooting
tests/                  Unit tests
```

---

## Development

```bash
bash scripts/setup.sh
source .venv/bin/activate
pytest -q
ruff check desain tests utils
```

CI runs lint and tests on Python 3.10 and 3.12.

---

## Roadmap

### Done
- Desktop chat UI with Photoshop design agent
- Local model auto-detection and model-aware tool strategies
- JSON action parsing with repair/retry for small models
- UXP + COM Photoshop bridges with checkpoints and validation
- Optional MCP server for external agents
- Automated tests and CI

### Planned
- Stronger Arabic / RTL typography
- Better multi-line hero font-size estimation
- Semantic template matching
- Brand kit support
- Template marketplace
- Optional web UI
- Unsplash vision rerank
- ComfyUI / Stable Diffusion as an imagery source

---

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) and [docs/limitations.md](docs/limitations.md).

---

## Contributing

1. Fork and branch from `main`
2. Keep Photoshop calls behind the bridge / client facades
3. Add unit tests for parser and agent helpers
4. Update docs when user-facing behavior changes
5. Open a focused pull request

---

## Commercial use

Commercial use requires prior written permission from the maintainer. Open a
GitHub issue titled `[Commercial License Request]`.

---

## License

Source-Available, Non-Commercial. See [`LICENSE`](LICENSE).

Adobe Photoshop, LM Studio, Ollama, llama.cpp, and Unsplash are subject to their
own terms when used with DES.ai.N.

---

<p align="center">
  <a href="https://github.com/mdluex/DES.ai.N/">Star on GitHub</a>
  ·
  <a href="docs/setup.md">Setup</a>
  ·
  <a href="docs/architecture.md">Architecture</a>
</p>
