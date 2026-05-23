<p align="center">
  <img src="logo.png" alt="DES-ai-N Logo" width="800"/>
</p>

<h1 align="center">Des-ai-N — AI Graphic Designer</h1>

<p align="center">
  An autonomous AI-powered design engine that controls <b>Adobe Photoshop</b> through natural language.<br/>
  Chat with the AI, and it builds, edits, and quality-checks professional marketing designs for you — all inside Photoshop.
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python"></a>
  <a href="https://www.adobe.com/products/photoshop.html"><img src="https://img.shields.io/badge/Adobe-Photoshop-31A8FF?logo=adobephotoshop" alt="Photoshop"></a>
  <a href="https://lmstudio.ai/"><img src="https://img.shields.io/badge/LLM-LM%20Studio-8B5CF6" alt="LM Studio"></a>
  <a href="https://github.com/mdluex/DES.ai.N/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Source%20Available%20%7C%20Non--Commercial-orange.svg" alt="License: Source Available, Non-Commercial"></a>
  <a href="#-commercial-use"><img src="https://img.shields.io/badge/Commercial%20Use-Permission%20Required-red.svg" alt="Commercial Use: Permission Required"></a>
  <img src="https://img.shields.io/badge/status-active%20development-success" alt="Status: Active">
  <a href="https://github.com/mdluex/DES.ai.N/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
</p>

<p align="center">
  <a href="https://github.com/mdluex/DES.ai.N/stargazers"><img src="https://img.shields.io/github/stars/mdluex/DES.ai.N?style=social" alt="Stars"></a>
  <a href="https://github.com/mdluex/DES.ai.N/network/members"><img src="https://img.shields.io/github/forks/mdluex/DES.ai.N?style=social" alt="Forks"></a>
  <a href="https://github.com/mdluex/DES.ai.N/issues"><img src="https://img.shields.io/github/issues/mdluex/DES.ai.N" alt="Issues"></a>
  <a href="https://github.com/mdluex/DES.ai.N/commits/main"><img src="https://img.shields.io/github/last-commit/mdluex/DES.ai.N" alt="Last commit"></a>
</p>

> **🚧 This project is under active development.**
> Des-ai-N is an ongoing research/engineering project exploring how local LLMs can drive a full-featured creative tool like Photoshop. APIs, prompts, and tool definitions evolve frequently — expect breaking changes. **Pull requests, issues, ideas, and design feedback are very welcome.**

---

## 📖 Table of Contents

- [Features](#-features)
- [Requirements](#-requirements)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Available AI Tools](#%EF%B8%8F-available-ai-tools)
- [Template Inspector](#-template-inspector)
- [How the Vision QA Works](#-how-the-vision-qa-works)
- [Configuration](#%EF%B8%8F-configuration)
- [Roadmap](#%EF%B8%8F-roadmap)
- [Contributing](#-contributing)
- [Community & Support](#-community--support)
- [Commercial Use](#-commercial-use)
- [License](#-license)

---

## ✨ Features

| Feature | Description |
|---|---|
| **Chat-First UI** | Modern dark-themed interface with real-time chat bubbles. Talk to the AI like a creative partner. |
| **Template Intelligence** | Automatically finds and opens matching `.psd` and `.psb` (large-document) templates from your library based on semantic similarity. |
| **Deep Vision Analysis** | On first open, the AI visually breaks down the template — locating headlines, CTAs, shapes, and fonts — before making any edits. |
| **Reference Image Recreation** | Upload any design and the AI decomposes it into editable layers (text, shapes, objects) and rebuilds it in Photoshop with pixel-accurate coordinates. |
| **Vision QA Loop** | Before saving, an internal Art Director inspects the design up to 4 rounds, checking for cropped text, overflow, contrast issues, and auto-fixes them. |
| **Font Awareness** | Detects all fonts used in the PSD and ensures new text layers stay consistent with the document's typography. |
| **Multi-Variation** | Ask for "3 different versions" and the AI builds each one sequentially, saving and closing between variations. |
| **Unsplash Integration** | Automatically downloads high-quality stock images from Unsplash and places them as background layers. |
| **Safe Text Placement** | All text positions are clamped inside canvas bounds — no more text appearing off-screen. |
| **Live Preview** | The right panel shows a real-time preview of the design as the AI works on it. |

---

## 📋 Requirements

- **Windows 10/11**
- **Python 3.10+**
- **Adobe Photoshop** (any version with COM/scripting support)
- **LM Studio** (or any OpenAI-compatible local LLM server)
  - Must have a vision-capable model loaded (e.g. LLaVA, Gemini, etc.)

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/mdluex/DES.ai.N.git
cd DES.ai.N
```

### 2. Run the launcher

Double-click **`run.bat`** — it will:
- ✅ Check that Python is installed
- ✅ Automatically install all dependencies (`PyQt5`, `openai`, `requests`, `pywin32`)
- ✅ Create `templates/` and `output/` folders if missing
- ✅ Launch the application

### 3. Configure (first time only)

Open the **Settings** tab and set:

| Setting | Description |
|---|---|
| **LM Studio Base URL** | Default: `http://localhost:1234/v1` |
| **API Key** | Your LM Studio API key |
| **Templates Folder** | Where your `.psd` templates live |
| **Output Folder** | Where finished designs are exported |
| **Save Source PSD** | Check this to also save `.psd` files alongside the PNGs |

### 4. Start designing

Switch to the **AI Workspace** tab and type a prompt:

```
Create a luxury watch ad with gold and black theme
```

```
Open the ego template and change the headline to "Ride the Future"
```

The AI will:
1. Search your templates for a match (or create a blank canvas)
2. Visually analyze the template structure
3. Make edits (text, colors, images, fonts)
4. Run Vision QA to ensure everything looks perfect
5. Export the final PNG to your output folder

---

## 📁 Project Structure

```
V13/
├── main.py                  # Entry point — launches UI + backend
├── run.bat                  # One-click launcher with auto-install
├── requirements.txt         # Python dependencies
├── theme.qss                # Dark UI stylesheet
│
├── core/
│   ├── ai_agent.py          # AI brain — LLM reasoning, vision QA, tool execution
│   └── photoshop_client.py  # Photoshop COM interface — all PS operations
│
├── ui/
│   ├── layout.py            # PyQt5 UI layout definition
│   └── main_window.py       # Main window logic, chat rendering, signals
│
├── utils/
│   ├── config.py            # API keys and defaults
│   ├── inspect_psd.py       # CLI utility — dumps a PSD's design DNA to JSON
│   └── unsplash.py          # Unsplash image downloader
│
├── templates/               # Place your .psd / .psb templates here
└── output/                  # Finished designs are saved here
```

---

## 🛠️ Available AI Tools

The AI agent has access to these Photoshop operations:

| Tool | Description |
|---|---|
| `open_template` | Open a PSD from the templates library |
| `create_canvas` | Create a blank canvas with custom dimensions |
| `add_text_layer` | Add text with font, size, color, position, rotation, letter-spacing |
| `set_layer_properties` | Edit text, font, size, opacity on existing layers |
| `move_layer` | Reposition a layer by pixel offset |
| `rotate_layer` / `scale_layer` | Rotate or uniformly scale a layer |
| `add_image_layer` | Download + place an Unsplash image as full-canvas background |
| `add_element_layer` | Download + place an Unsplash image as a positioned subject (optional bg-removal) |
| `add_solid_color_layer` | Add a color fill layer |
| `add_gradient_layer` | Add a two-color linear gradient |
| `add_shape` | Add a vector rectangle, circle, or ellipse with optional rotation |
| `add_stroke` | Add an outline layer style to a layer |
| `add_pill_cta` | Create a corner-anchored CTA pill (rounded rectangle + centered text) in one step |
| `change_shape_color` | Recolor an existing shape layer |
| `select_subject_and_mask` | Photoshop AI Select Subject + apply layer mask |
| `generate_fill` | Photoshop AI Generative Fill (PS 2024+ with Firefly) |
| `reorder_layer` | Move a layer up/down in the stack |
| `save_document` | Export as PNG (+ optional PSD) without closing |
| `close_document` | Close the active document without saving |
| `finalize_design` | Signal that all work is complete — auto-saves and runs QA |

---

## 🔬 Template Inspector

The repo ships with a CLI utility that opens any `.psd` or `.psb` via Photoshop COM
and prints its design DNA (canvas size, fonts, colors, layer hierarchy, text bounds):

```bash
python -m utils.inspect_psd "templates\FIGO Ride hailing app - Social media post.psd"
python -m utils.inspect_psd "templates\Mutqan Ramadan Banner.psb"
```

It writes a sibling `*.inspect.json` file next to the source file with every
layer's typography, fill color, bounds, blend mode, and group hierarchy. This is
useful for mining patterns out of professional templates and feeding the system
prompt with proven design ratios.

### About `.psb` (Photoshop Big) files

Des-ai-N treats `.psb` files as first-class templates. PSB is Photoshop's
"large-document" format for files that exceed the PSD limits (over 30,000 px on
either axis or larger than 2 GB). The agent will automatically:

- Detect `.psb` files when listing the `templates/` folder.
- Open them transparently when you ask (e.g. *"open the Mutqan banner"*).
- Save edited copies back as `.psb` instead of `.psd` when the canvas is too
  large for the PSD format.

---

## 🧠 How the Vision QA Works

```
┌─────────────────┐
│  AI Makes Edits │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Capture Preview │──→ Updates Live Preview panel
└────────┬────────┘
         ▼
┌─────────────────┐     ┌──────────────┐
│  Vision Agent   │────→│ Text cropped?│──→ Reduce font / shorten text
│  Inspects Image │     │ Off canvas?  │──→ Move layer inward
│                 │     │ Low contrast?│──→ Adjust colors
└────────┬────────┘     └──────────────┘
         ▼
    Pass? ──→ Yes ──→ ✅ Approve & Save
      │
      No ──→ Apply fixes ──→ Loop (up to 4 rounds)
```

---

## ⚙️ Configuration

Edit `utils/config.py` to change default API keys:

```python
UNSPLASH_KEY = 'your-unsplash-access-key'
DEFAULT_API_URL = "http://localhost:1234/v1"
DEFAULT_API_KEY = "your-lm-studio-key"
```

> ⚠️ **Don't commit real API keys.** Use a personal local copy or environment
> variables. A `.env`-based config is on the roadmap — see [Contributing](#-contributing)
> if you'd like to help build it.

---

## 🗺️ Roadmap

Des-ai-N is an ongoing project. Here's what's planned, what's in progress, and
where help is most welcome.

### ✅ Done
- Photoshop COM-driven design agent with 21+ tools
- Live preview panel + dark chat-first UI
- Deep vision analysis on template open
- Vision QA auto-fix loop (up to 4 rounds)
- Reference image → editable-layer recreation pipeline
- Per-PSD design-DNA inspector (`utils/inspect_psd.py`)
- Pro design patterns (pill CTA, accent bars, hero typography ratios)

### 🚧 In Progress
- Better Arabic / RTL typography support
- More accurate text-bbox → font-size estimation for multi-line hero text
- Smarter template matching (semantic embeddings instead of filename matching)

### 🎯 Planned / Help Wanted
- **macOS support** — replace `win32com` with the cross-platform Photoshop Scripting bridge
- **`.env`-based secret management** for API keys
- **Cloud LLM providers** (OpenAI, Anthropic, Google, Groq) alongside LM Studio
- **Plugin system** so users can register custom tools without forking the agent
- **Template marketplace** — curated PSDs with verified design-DNA reports
- **Brand kit support** — load brand colors/fonts/logo so the AI auto-applies them
- **Automated test suite** for the Photoshop client (mocked COM)
- **Web-based UI** as an optional alternative to PyQt5
- **Better Unsplash result ranking** using vision rerank
- **Stable Diffusion / ComfyUI integration** as an alternative to Generative Fill

> 💡 See any of these you'd like to tackle? Open an issue saying "I'd like to
> work on X" and we'll scope it together.

---

## 🤝 Contributing

Contributions of all sizes are warmly welcome — bug reports, feature ideas,
docs improvements, prompt tuning, new tools, new templates, or full PRs.

### Where to start

1. ⭐ **Star the repo** — [github.com/mdluex/DES.ai.N](https://github.com/mdluex/DES.ai.N/) — it helps visibility.
2. 🐛 **Try it and break it.** File an [Issue](https://github.com/mdluex/DES.ai.N/issues) with what you tried, what you expected, and what you got (screenshots help a lot).
3. 💬 **Discuss your idea first** for anything bigger than a small fix — open an issue or start a discussion so we can align on direction before you spend time coding.
4. 🍴 **Fork the repo, send a PR.** See below.

### Good first issues

- Add new color palettes to the system prompt in `core/ai_agent.py`
- Add a new pro design pattern (e.g. "split-screen banner", "magazine cover")
- Add a new high-value tool to `PhotoshopClient` (e.g. `add_drop_shadow`, `add_inner_glow`)
- Improve `utils/inspect_psd.py` to also extract layer effects (strokes, shadows)
- Translate the system prompt to other languages
- Donate professionally-designed PSD templates to the `templates/` showcase folder

### Local development setup

```bash
# 1. Fork on GitHub, then clone your fork
git clone https://github.com/<your-username>/DES.ai.N.git
cd DES.ai.N

# 2. Create a feature branch
git checkout -b feat/short-descriptive-name

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the app once to make sure it runs
python main.py
```

### Pull request workflow

1. Keep PRs **focused** — one feature/fix per PR. Smaller is better.
2. Match the existing code style — 4-space indentation, snake_case, descriptive names, comments only for non-obvious intent.
3. **Test on a real Photoshop install** before submitting. If your change touches the agent loop, also test the reference-image recreation flow.
4. Update the **README** and **roadmap** if you add a user-visible feature.
5. Reference the issue your PR closes (`Closes #123`) in the description.
6. Be patient — this is a hobby/research project, reviews may take a few days.

### Coding guidelines

- **Python**: target 3.10+. Prefer standard-library solutions over heavy dependencies.
- **Photoshop ops**: all Photoshop calls go through `core/photoshop_client.py`. Don't sprinkle COM calls elsewhere.
- **Agent tools**: when adding a new tool, update **(1)** `PhotoshopClient` method, **(2)** `get_tools()` schema, **(3)** the `run_agent_loop` dispatcher, **(4)** the system prompt, and **(5)** the README tool table.
- **Prompts**: keep prompts in `core/ai_agent.py`. Use the existing section headers (`━━━` blocks) for consistency.
- **No secrets in commits.** Treat `utils/config.py` as a template, not a place for real keys.

### Reporting bugs

When filing an issue, please include:
- OS + Photoshop version
- Python version (`python --version`)
- LM Studio model name (vision-capable?)
- A copy-paste of the chat prompt that triggered the problem
- The terminal output (especially any `[ERROR]` lines)
- A screenshot of the broken design if applicable

### Contributor License Agreement (implicit)

By opening a pull request to this repository, you confirm that:

- You have the right to contribute the code/content you are submitting.
- You retain copyright over your contribution.
- You agree that your contribution may be distributed under the project's
  [Source-Available Non-Commercial License](LICENSE), **including potential
  relicensing under separate commercial agreements** as described in the
  [Commercial Use](#-commercial-use) section.

This keeps the project welcoming to contributors while preserving the
maintainer's ability to grant commercial licenses on request.

### Code of Conduct

Be kind. Assume good faith. Critique the code, never the person. Discriminatory
or harassing behaviour will not be tolerated.

---

## 💬 Community & Support

- **🐛 Bug reports & feature requests** → [GitHub Issues](https://github.com/mdluex/DES.ai.N/issues)
- **🔀 Pull requests** → [GitHub PRs](https://github.com/mdluex/DES.ai.N/pulls)
- **🌟 Star history** → If Des-ai-N saved you time, please consider starring the repo!

---

## 💼 Commercial Use

> **🛑 Commercial use of Des-ai-N requires prior written permission from the maintainer.**
> The project is free for personal, educational, research, and other non-commercial use,
> but **any commercial use must be authorised in writing before you start.**

### What counts as commercial use?

Commercial use includes, but is not limited to:

| ✅ Free (Non-Commercial) | 🛑 Requires Permission (Commercial) |
|---|---|
| Personal projects and hobby designs | Selling, licensing, or monetising designs produced with Des-ai-N |
| Learning, teaching, or academic research | Paid client / freelance / agency work using the tool |
| Trying it out (≤30 days evaluation) | Bundling or embedding Des-ai-N into a paid product, SaaS, or service |
| Open-source contributions back to this repo | Internal production use inside a for-profit organisation |
| Sharing screenshots / writeups / tutorials | Reselling, sublicensing, or redistributing Des-ai-N for a fee |

### How to request a commercial license

If your use case falls on the right side of the table above — or you're unsure
— **contact the maintainer first**. Approval is usually quick and friendly,
but it must happen *before* commercial use begins.

**Preferred:** Open a GitHub issue with the prefix **`[Commercial License Request]`** at
[github.com/mdluex/DES.ai.N/issues](https://github.com/mdluex/DES.ai.N/issues)
and include:

1. **Who you are** — name / company / website
2. **What you want to use it for** — paid client work, internal tool, SaaS product, etc.
3. **Scale** — solo freelancer / small team / enterprise
4. **Deployment context** — local-only / cloud-hosted / customer-facing

**Alternative:** Reach out via the contact methods listed on the maintainer's
GitHub profile at [github.com/mdluex](https://github.com/mdluex).

Using Des-ai-N for commercial purposes without prior written permission is a
material breach of the license and automatically terminates all rights to use
the Software.

---

## 📄 License

Des-ai-N is released under a custom **Source-Available, Non-Commercial License**.
The short version:

- ✅ **Free** for personal, educational, research, and other non-commercial use.
- ✅ **Free** to fork, modify, and submit pull requests back to this repo.
- ✅ **Free** to share the source code, provided this license notice stays intact.
- 🛑 **Commercial use requires prior written permission** — see [Commercial Use](#-commercial-use).
- 🛑 No warranty of any kind. Use at your own risk.

**Contributors:** by submitting a pull request you agree that your contribution
may be relicensed by the maintainer under separate commercial agreements per
the license terms. You retain copyright over your own contribution.

See the full [`LICENSE`](LICENSE) file for the binding legal text. If anything
in this README conflicts with the `LICENSE` file, the `LICENSE` file controls.

> **Third-party services:** This project integrates with Adobe Photoshop, LM Studio,
> and Unsplash. Their respective terms of service apply when you use those services
> through Des-ai-N.

---

<p align="center">
  Made with ☕ and a lot of vision-model retries.<br/>
  <a href="https://github.com/mdluex/DES.ai.N/">⭐ Star us on GitHub</a> if you find this useful.<br/>
  Need commercial use? <a href="https://github.com/mdluex/DES.ai.N/issues/new?title=%5BCommercial+License+Request%5D+">Open a commercial license request</a>.
</p>
