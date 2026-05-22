<p align="center">
  <img src="logo.png" alt="DES-ai-N Logo" width="800"/>
</p>

# Des-ai-N — AI Graphic Designer

An autonomous AI-powered design engine that controls **Adobe Photoshop** through natural language. Chat with the AI, and it builds, edits, and quality-checks professional marketing designs for you — all inside Photoshop.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Photoshop](https://img.shields.io/badge/Adobe-Photoshop-31A8FF?logo=adobephotoshop)
![LM Studio](https://img.shields.io/badge/LLM-LM%20Studio-8B5CF6)

---

## ✨ Features

| Feature | Description |
|---|---|
| **Chat-First UI** | Modern dark-themed interface with real-time chat bubbles. Talk to the AI like a creative partner. |
| **Template Intelligence** | Automatically finds and opens matching PSD templates from your library based on semantic similarity. |
| **Deep Vision Analysis** | On first open, the AI visually breaks down the template — locating headlines, CTAs, shapes, and fonts — before making any edits. |
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

### 1. Clone or download the project

Place the project folder anywhere on your system.

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
│   └── unsplash.py          # Unsplash image downloader
│
├── templates/               # Place your .psd templates here
└── output/                  # Finished designs are saved here
```

---

## 🛠️ Available AI Tools

The AI agent has access to these Photoshop operations:

| Tool | Description |
|---|---|
| `open_template` | Open a PSD from the templates library |
| `create_canvas` | Create a blank canvas with custom dimensions |
| `add_text_layer` | Add text with font, size, color, and position |
| `set_layer_properties` | Edit text, font, size, opacity on existing layers |
| `move_layer` | Reposition a layer by pixel offset |
| `add_image_layer` | Download + place an Unsplash image |
| `add_solid_color_layer` | Add a color fill layer |
| `add_pill_cta` | Create a corner-anchored CTA pill (rounded rectangle + centered text) in one step — the FIGO-style hero CTA pattern |
| `save_and_close_document` | Export as PNG (+ optional PSD) and close |
| `finalize_design` | Signal that all work is complete |

---

## 🔬 Template Inspector

The repo ships with a CLI utility that opens any PSD via Photoshop COM and prints
its design DNA (canvas size, fonts, colors, layer hierarchy, text bounds):

```bash
python -m utils.inspect_psd "templates\FIGO Ride hailing app - Social media post.psd"
```

It writes a sibling `*.inspect.json` file next to the PSD with every layer's
typography, fill color, bounds, blend mode, and group hierarchy. This is useful
for mining patterns out of professional templates and feeding the system prompt
with proven design ratios.

---

## 🧠 How the Vision QA Works

```
┌─────────────────┐
│  AI Makes Edits  │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Capture Preview  │──→ Updates Live Preview panel
└────────┬────────┘
         ▼
┌─────────────────┐     ┌──────────────┐
│  Vision Agent    │────→│ Text cropped? │──→ Reduce font / shorten text
│  Inspects Image  │     │ Off canvas?   │──→ Move layer inward
│                  │     │ Low contrast? │──→ Adjust colors
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

---

## 📄 License

This project is for personal and educational use.
