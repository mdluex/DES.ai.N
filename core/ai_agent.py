import json
import os
import time
import base64
import tempfile
from openai import OpenAI
from utils.unsplash import get_image_from_unsplash


class DesignAgent:
    def __init__(self, api_url, api_key, ps_client, output_folder, templates_folder, log_callback=None, preview_callback=None):
        self.api_url = api_url
        self.api_key = api_key
        self.ps_client = ps_client
        self.output_folder = output_folder
        self.templates_folder = templates_folder
        self.log = log_callback or print
        self.preview_callback = preview_callback
        self.messages = []
        self.save_psd = False
        self.template_cache = {}  # {filename: visual_breakdown_text}
        self.edit_log = []  # tracks every edit made in current design session

    # ── LLM helpers ──────────────────────────────────────────────────

    def _get_client(self):
        return OpenAI(base_url=self.api_url, api_key=self.api_key)

    def get_model(self):
        try:
            client = self._get_client()
            models = client.models.list()
            if models.data:
                return models.data[0].id
        except Exception as e:
            self.log(f"[SYSTEM] Could not fetch models from LM Studio: {e}")
        return "local-model"

    # ── Tool definitions ─────────────────────────────────────────────

    def get_tools(self):
        return [
            {"type":"function","function":{"name":"open_template","description":"Open an existing PSD template from the library.","parameters":{"type":"object","properties":{"filename":{"type":"string","description":"Name of the .psd file"}},"required":["filename"]}}},
            {"type":"function","function":{"name":"create_canvas","description":"Create a new blank Photoshop canvas.","parameters":{"type":"object","properties":{"width":{"type":"integer"},"height":{"type":"integer"},"filename":{"type":"string"}},"required":["width","height","filename"]}}},
            {"type":"function","function":{"name":"save_document","description":"Export the current design as PNG (and PSD if enabled). Does NOT close the document.","parameters":{"type":"object","properties":{"filename":{"type":"string","description":"Base filename without extension"}},"required":["filename"]}}},
            {"type":"function","function":{"name":"close_document","description":"Close the current document WITHOUT saving. Only use when the user asks to close.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"add_image_layer","description":"Download a high-quality image from Unsplash and place it as a background layer.","parameters":{"type":"object","properties":{"keyword":{"type":"string","description":"1-2 word Unsplash search term"},"blend_mode":{"type":"integer","description":"1=Normal,5=Multiply,7=Screen,16=Overlay"},"opacity":{"type":"integer","description":"0-100"}},"required":["keyword"]}}},
            {"type":"function","function":{"name":"add_solid_color_layer","description":"Add a solid colour fill layer.","parameters":{"type":"object","properties":{"hex_color":{"type":"string"},"blend_mode":{"type":"integer"},"opacity":{"type":"integer"}},"required":["hex_color"]}}},
            {"type":"function","function":{"name":"add_gradient_layer","description":"Add a two-colour linear gradient layer.","parameters":{"type":"object","properties":{"hex_color1":{"type":"string"},"hex_color2":{"type":"string"},"angle":{"type":"integer","description":"0=left-right, 90=top-bottom"},"blend_mode":{"type":"integer"},"opacity":{"type":"integer"}},"required":["hex_color1","hex_color2"]}}},
            {"type":"function","function":{"name":"add_shape","description":"Create a vector shape layer (rectangle, circle, or ellipse) with solid colour fill. For a perfect circle use shape_type='circle' and equal width/height.","parameters":{"type":"object","properties":{"shape_type":{"type":"string","enum":["rectangle","ellipse","circle"],"description":"Shape type: rectangle, ellipse (oval), or circle (perfect circle)"},"x":{"type":"integer","description":"Top-left X"},"y":{"type":"integer","description":"Top-left Y"},"width":{"type":"integer","description":"Shape width in px"},"height":{"type":"integer","description":"Shape height in px (set equal to width for a perfect circle)"},"hex_color":{"type":"string","description":"Fill colour hex"},"corner_radius":{"type":"integer","description":"Corner radius for rectangles (0=sharp)"},"opacity":{"type":"integer"},"rotation":{"type":"number","description":"Rotation angle in degrees around the shape center. Positive = clockwise. Use for tilted/skewed accent bars."}},"required":["shape_type","x","y","width","height","hex_color"]}}},
            {"type":"function","function":{"name":"add_text_layer","description":"Add a text layer. Position is auto-corrected to stay inside the canvas. y is the text BASELINE. For center alignment, x should be the horizontal center point of the text.","parameters":{"type":"object","properties":{"content":{"type":"string"},"font_size":{"type":"integer"},"hex_color":{"type":"string","description":"Text color as hex code (e.g. #FF0000) or color name"},"x":{"type":"integer","description":"X position in px (left edge for left-align, center for center-align)"},"y":{"type":"integer","description":"Y baseline position in px"},"alignment":{"type":"string","enum":["left","center","right"],"description":"Text alignment. Default left."},"blend_mode":{"type":"integer"},"opacity":{"type":"integer"},"font_name":{"type":"string","description":"PostScript font name. For BOLD hero text, append '-Bold' or '-Black'. For CONDENSED, use families like 'Oswald','Bebas Neue','BebasNeue-Regular','Anton-Regular','Impact','HelveticaNeue-CondensedBold'."},"rotation":{"type":"number","description":"Rotation angle in degrees around the text center. Positive = clockwise."},"letter_spacing":{"type":"number","description":"Tracking value (-200 to 1000). Negative = tighter (good for hero/condensed text)."}},"required":["content","font_size","hex_color","x","y"]}}},
            {"type":"function","function":{"name":"set_layer_properties","description":"Modify an existing layer's text, font, colour, size, opacity, or blend mode.","parameters":{"type":"object","properties":{"index":{"type":"integer"},"text":{"type":"string"},"font_size":{"type":"integer"},"font_name":{"type":"string"},"hex_color":{"type":"string"},"opacity":{"type":"integer"},"blend_mode":{"type":"integer"}},"required":["index"]}}},
            {"type":"function","function":{"name":"move_layer","description":"Translate a layer by pixel offsets. Use bounds to calculate deltas.","parameters":{"type":"object","properties":{"index":{"type":"integer"},"delta_x":{"type":"integer"},"delta_y":{"type":"integer"}},"required":["index","delta_x","delta_y"]}}},
            {"type":"function","function":{"name":"rotate_layer","description":"Rotate a layer by degrees around its center.","parameters":{"type":"object","properties":{"index":{"type":"integer"},"angle":{"type":"number","description":"Rotation angle in degrees (positive=clockwise)"}},"required":["index","angle"]}}},
            {"type":"function","function":{"name":"scale_layer","description":"Scale a layer uniformly by percentage (100=no change, 50=half, 200=double).","parameters":{"type":"object","properties":{"index":{"type":"integer"},"scale_percent":{"type":"number","description":"Scale percentage"}},"required":["index","scale_percent"]}}},
            {"type":"function","function":{"name":"add_stroke","description":"Add a stroke (outline) layer style to a layer.","parameters":{"type":"object","properties":{"index":{"type":"integer"},"thickness":{"type":"integer","description":"Stroke width in pixels"},"hex_color":{"type":"string","description":"Stroke colour hex"}},"required":["index","thickness","hex_color"]}}},
            {"type":"function","function":{"name":"reorder_layer","description":"Move a layer to a different position in the layer stack.","parameters":{"type":"object","properties":{"index":{"type":"integer","description":"Current layer index"},"new_index":{"type":"integer","description":"Target layer index (0=top)"}},"required":["index","new_index"]}}},
            {"type":"function","function":{"name":"select_subject_and_mask","description":"Use Photoshop AI to auto-select the subject on a layer and apply a layer mask. Great for isolating people/objects from backgrounds.","parameters":{"type":"object","properties":{"index":{"type":"integer","description":"Layer index to select subject on"}},"required":["index"]}}},
            {"type":"function","function":{"name":"add_element_layer","description":"Download an image from Unsplash and place it as a positioned element (NOT full-canvas). Use for foreground subjects, collage pieces, or photo manipulation elements. Set remove_background=true to auto-isolate the subject.","parameters":{"type":"object","properties":{"keyword":{"type":"string","description":"1-3 word Unsplash search term"},"x":{"type":"integer","description":"X position (left edge)"},"y":{"type":"integer","description":"Y position (top edge)"},"width":{"type":"integer","description":"Element width in px"},"height":{"type":"integer","description":"Element height in px"},"remove_background":{"type":"boolean","description":"If true, auto-remove background using AI Select Subject + mask"},"blend_mode":{"type":"integer","description":"1=Normal,5=Multiply,7=Screen,16=Overlay"},"opacity":{"type":"integer","description":"0-100"},"rotation":{"type":"number","description":"Rotation angle in degrees around the element center."}},"required":["keyword","x","y","width","height"]}}},
            {"type":"function","function":{"name":"generate_fill","description":"Use Photoshop AI Generative Fill to generate AI content in a selected area. Requires Photoshop 2024+ with Adobe Firefly.","parameters":{"type":"object","properties":{"prompt":{"type":"string","description":"Description of what to generate"},"x":{"type":"integer","description":"X position of fill area"},"y":{"type":"integer","description":"Y position of fill area"},"width":{"type":"integer","description":"Width of fill area"},"height":{"type":"integer","description":"Height of fill area"}},"required":["prompt","x","y","width","height"]}}},
            {"type":"function","function":{"name":"change_shape_color","description":"Change the fill colour of an existing shape layer by its index.","parameters":{"type":"object","properties":{"index":{"type":"integer","description":"Layer index of the shape"},"hex_color":{"type":"string","description":"New fill colour as hex (e.g. #FF0000)"}},"required":["index","hex_color"]}}},
            {"type":"function","function":{"name":"add_pill_cta","description":"Create a PRO-style 'corner-anchored CTA pill' in ONE call: a rounded rectangle + perfectly centered text on top. This is the FIGO-style hero CTA pattern — prefer this over manually composing shape+text. Pill is fully-rounded by default.","parameters":{"type":"object","properties":{"text":{"type":"string","description":"The CTA text (keep short: 1-4 words)"},"x":{"type":"integer","description":"Top-left X of the pill"},"y":{"type":"integer","description":"Top-left Y of the pill"},"width":{"type":"integer","description":"Pill width in px"},"height":{"type":"integer","description":"Pill height in px"},"pill_color":{"type":"string","description":"Pill fill hex (brand accent color)"},"text_color":{"type":"string","description":"CTA text hex (default #ffffff)"},"font_size":{"type":"integer","description":"Optional. Auto-sized to ~38% of pill height if omitted."},"font_name":{"type":"string","description":"Optional PostScript font name for the text"},"corner_radius":{"type":"integer","description":"Optional. Fully rounded (height/2) by default."}},"required":["text","x","y","width","height","pill_color"]}}},
            {"type":"function","function":{"name":"finalize_design","description":"Call when ALL requested work is complete. Saves the design automatically.","parameters":{"type":"object","properties":{"message":{"type":"string","description":"Summary of what was created"},"filename":{"type":"string","description":"Base filename for export"}},"required":["message","filename"]}}}

        ]

    # ── Session management ───────────────────────────────────────────

    def init_session(self, prompt, available_templates, save_psd=False):
        self.save_psd = save_psd
        system_prompt = (
            "You are an elite Creative Director controlling Adobe Photoshop via a Python tool API. "
            "Your job is to create designs that look like they came from a top professional design agency.\n"
            f"Available PSD templates: {available_templates}\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  WORKFLOW\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "1. If a template matches the prompt → open_template. Otherwise → create_canvas.\n"
            "2. After EVERY tool call, READ the returned bounds carefully.\n"
            "3. Call finalize_design when ALL work is done — it auto-saves.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  READING THE LAYER MAP (CRITICAL)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "When a template is opened or layer context is returned, you receive a LAYER MAP:\n"
            "  [idx] kind  \'name\'  op=%  blend=X\n"
            "    pos=(left,top) size=WxH center=(cx,cy)\n"
            "    TEXT: \"content\"  font=X  size=Xpt  color=#RRGGBB  align=X\n"
            "    text_pos=[x,y]  leading=X  tracking=X\n\n"
            "RULES for using the layer map:\n"
            "- The INDEX number is what you pass to move_layer, set_layer_properties, scale_layer, etc.\n"
            "- bounds.left/top = where layer starts. bounds.right/bottom = where it ends.\n"
            "- bounds.center_x/center_y = geometric center. Use for centering calculations.\n"
            "- text_pos=[x,y] = TEXT BASELINE anchor point. For add_text_layer, y IS the baseline.\n"
            "  Baseline ≈ top_of_text + font_size * 0.8\n"
            "- font = exact PostScript font name. Use this when matching existing styles.\n"
            "- color_hex = exact hex color. Match it when recreating template layers.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  COORDINATE SYSTEM & SPATIAL PLANNING\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "BEFORE placing anything, plan the full layout first. For a W x H canvas:\n"
            "  ZONES:   top=0..H*0.25 | upper_mid=H*0.25..H*0.5 | lower_mid=H*0.5..H*0.75 | bottom=H*0.75..H\n"
            "  MARGINS: left=W*0.07   right=W*0.93   safe_width=W*0.86\n"
            "  CENTER:  cx=W//2  cy=H//2\n\n"
            "TEXT BASELINE MATH:\n"
            "  baseline_y = zone_top + font_size * 0.8\n"
            "  next_line_y = baseline_y + leading (or font_size * 1.3 if no leading)\n"
            "  For LEFT-aligned:   x = left_margin (e.g. W*0.07)\n"
            "  For CENTER-aligned: x = W//2  (Photoshop centers around this point)\n"
            "  For RIGHT-aligned:  x = right_edge (e.g. W*0.93)\n\n"
            "EXAMPLE for 1080×1080 canvas:\n"
            "  Headline (size=90, centered):  x=540, y=370\n"
            "  Subline  (size=42, centered):  x=540, y=480  [gap=90*1.3≈117 → 370+117=487]\n"
            "  CTA text (size=28, centered):  x=540, y=820\n"
            "  CTA button shape:              x=290, y=760, w=500, h=70\n\n"

            "NON-OVERLAP RULES — NEVER VIOLATE:\n"
            "- After each tool call, note the returned bounds of the new layer.\n"
            "- Before placing the next text/shape, check: will it overlap the previous bounds?\n"
            "  Overlap if: new_top < prev_bottom  AND  new_left < prev_right AND new_right > prev_left\n"
            "- If overlap: set new_top = prev_bottom + gap (gap ≥ 20px minimum)\n"
            "- Minimum vertical gap between text layers = max(size1, size2) * 0.3\n"
            "- NEVER place text at x<50 or y<50 or x>canvas_w-50 or y>canvas_h-20.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  PROFESSIONAL TEMPLATE PATTERNS\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Patterns extracted from a real, professionally-designed 1400×1400 social\n"
            "media post. Apply these proportional rules to any square canvas WxH:\n\n"

            "TYPOGRAPHIC HIERARCHY (proven ratios, scale by canvas height H):\n"
            "  Hero headline      → font_size ≈ H * 0.083  (e.g. 117pt on 1400, 90pt on 1080)\n"
            "  Secondary CTA      → font_size ≈ H * 0.073  (e.g. 102pt on 1400, 79pt on 1080)\n"
            "  Tagline / sub-cta  → font_size ≈ H * 0.036  (e.g.  50pt on 1400, 39pt on 1080)\n"
            "  Body / footnote    → font_size ≈ H * 0.018  (e.g.  25pt on 1400, 20pt on 1080)\n"
            "  → Always create at least a 2× size gap between two consecutive text levels.\n\n"

            "LAYER STACK ORDER (build bottom-up — DO NOT skip steps):\n"
            "  1. BG fill          (full canvas solid or gradient — the brand color)\n"
            "  2. Atmosphere       (large image at 80% opacity, blend=Multiply, can bleed off canvas)\n"
            "  3. Hero subject     (centered, ~55-65% of canvas height, on its own layer)\n"
            "  4. Accent shape     (rectangle behind headline OR pill behind CTA — see below)\n"
            "  5. Headline text    (above accent, top zone)\n"
            "  6. CTA pill shape   (large rounded rectangle in a corner — see PILL CTA)\n"
            "  7. CTA text         (white, centered over the pill)\n"
            "  8. Brand mark       (logo or icon in top-left corner)\n"
            "  9. Footer marks     (download icons / secondary CTAs in bottom-left)\n\n"

            "CORNER ANCHORING (PRO INSTINCT):\n"
            "  Top-left corner    = brand logo at margin ≈ W*0.06 (e.g. (86,86) on 1400)\n"
            "  Top zone           = headline (centered horizontally, top 30%)\n"
            "  Center             = hero subject / product photo\n"
            "  Bottom-right       = CTA pill + CTA text   (action drives the eye here)\n"
            "  Bottom-left        = secondary CTAs / download buttons / app store icons\n\n"

            "ACCENT RECTANGLE BEHIND HEADLINE (TYPOGRAPHIC PUNCH):\n"
            "  Place a contrasting rectangle slightly BEHIND the headline that overshoots\n"
            "  the text bounds by ~10-30px. It sits on the lower half of the text block:\n"
            "    rect_left   = headline_left  - 10\n"
            "    rect_top    = headline_top   + headline_height * 0.45\n"
            "    rect_width  = headline_width + 20\n"
            "    rect_height = headline_height * 0.65\n"
            "  Then place the headline AFTER the rectangle so the text sits on top.\n"
            "  Use a vivid brand color for the rectangle (orange, red, yellow) when text is white.\n\n"

            "PILL CTA (BOTTOM-RIGHT, CORNER-ANCHORED):\n"
            "  pill = add_shape('rectangle', x=W*0.53, y=H*0.81, width=W*0.47, height=H*0.19,\n"
            "                   hex_color=BRAND_ACCENT, corner_radius=40)\n"
            "  IMPORTANT: the pill is allowed to bleed slightly OFF the right/bottom edges\n"
            "  (extend its right edge to W+10, bottom to H+10) — gives a confident edge-bleed look.\n"
            "  Then add CTA text CENTERED inside this pill:\n"
            "    cta_x = pill_left + pill_width // 2\n"
            "    cta_y = pill_top  + pill_height // 2 + font_size * 0.3\n"
            "    add_text_layer(content='SHOP NOW', font_size=H*0.036, hex_color='#ffffff',\n"
            "                   x=cta_x, y=cta_y, alignment='center')\n\n"

            "EDGE BLEED (CONFIDENT PRO LOOK):\n"
            "  Pro templates intentionally let large hero shapes/photos extend ~3% past the\n"
            "  canvas edge. This means: shape x can be -30, width can extend to W+30.\n"
            "  But TEXT must ALWAYS stay inside (≥50px from every edge).\n\n"

            "MULTI-LAYER BACKGROUND (CINEMATIC TEXTURE — 3-LAYER STACK):\n"
            "  Layer A: solid color or gradient (the brand base color)\n"
            "  Layer B: large textured photo, opacity=80, blend=Multiply (#4) — adds grit/depth\n"
            "  Layer C: same photo duplicated, blend=Difference (#19) at 100% — subtle pop\n"
            "  Result: rich, atmospheric backdrop instead of flat color.\n\n"

            "GROUP THINKING (think in SECTIONS not flat layers):\n"
            "  Plan in 6 conceptual groups before placing anything:\n"
            "    [BG] [Atmosphere/Elements] [Hero Subject] [Headline+Accent] [CTA Pill+Text] [Brand+Footer]\n"
            "  Build them in this exact order — never place a text layer before its background shape.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  EDITING EXISTING LAYERS (template mode)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "1. Read the full LAYER MAP before making any edits.\n"
            "2. Use set_layer_properties(index, text=, hex_color=, font_size=, font_name=) to change layers.\n"
            "3. Use move_layer(index, delta_x, delta_y) — delta is the OFFSET, not absolute position.\n"
            "   To move to absolute pos: delta_x = target_left - bounds.left\n"
            "4. scale_layer(index, scale_percent) — uniform scale, preserves aspect ratio.\n"
            "5. change_shape_color(index, hex) — recolor a solid shape.\n"
            "6. rotate_layer(index, angle) — rotate around center.\n"
            "7. CHARACTER LIMITS: When editing template text, count chars in the original. New\n"
            "   text should be within ±20% of the original length to fit the same visual box.\n"
            "8. FONT CONSISTENCY: If the template uses one font family, every new text layer\n"
            "   you add MUST use the same family (read it from the LAYER MAP `fonts_used`).\n"
            "PREFER editing existing layers over adding new ones in templates.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  CANVAS SIZES (USE THE RIGHT ONE)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  1080x1080  — Instagram square (default for unspecified social)\n"
            "  1400x1400  — High-resolution social post (Facebook, LinkedIn, ride-hailing style)\n"
            "  1080x1350  — Instagram portrait / feed-optimized\n"
            "  1080x1920  — Story / Reel / TikTok\n"
            "  1920x1080  — YouTube thumbnail / wide banner / Twitter header\n"
            "  1500x500   — Twitter header\n"
            "   800x1200  — Pinterest pin / portrait poster\n"
            "Choose 1400x1400 over 1080x1080 when the design needs large brand typography\n"
            "or detailed photographic hero subjects.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  DESIGN RECIPE (NEW CANVAS)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "STEP 1 — create_canvas (typical: 1400x1400 social, 1920x1080 banner, 800x1200 portrait)\n"
            "STEP 2 — BACKGROUND (choose one):\n"
            "  BRAND FILL: add_solid_color_layer(BRAND_COLOR)   ← then add textured atmosphere on top\n"
            "  CINEMATIC:  add_gradient_layer('#0a0a1a','#1a1a3e',angle=90)\n"
            "  VIBRANT:    add_gradient_layer('#2d1b69','#11998e')\n"
            "  PHOTO:      add_image_layer(keyword='...')\n"
            "STEP 3 — ATMOSPHERE: add_image_layer(keyword='abstract texture', opacity=80, blend_mode=4)\n"
            "          (Multiply blend with 80% opacity → adds depth without dominating)\n"
            "STEP 4 — HERO SUBJECT: add_element_layer(kw, x=W*0.17, y=H*0.31, width=W*0.67, height=H*0.56,\n"
            "                                        remove_background=true)\n"
            "STEP 5 — PLAN YOUR LAYOUT: write down all element y-positions before drawing anything.\n"
            "STEP 6 — ACCENT SHAPE behind headline (optional but recommended for punch):\n"
            "          add_shape('rectangle', x=margin, y=headline_y+headline_size*0.45,\n"
            "                    width=safe_width, height=headline_size*0.65, hex_color=BRAND_ACCENT)\n"
            "STEP 7 — TEXT (strict hierarchy):\n"
            "  HEADLINE  (size=H*0.083, color='#ffffff', center-aligned, top zone)\n"
            "  TAGLINE   (size=H*0.036, color='#ffffff' or accent, center-aligned, below headline)\n"
            "STEP 8 — CTA PILL (bottom-right corner):\n"
            "          add_shape('rectangle', x=W*0.53, y=H*0.81, width=W*0.47, height=H*0.19,\n"
            "                    hex_color=BRAND_ACCENT, corner_radius=40)\n"
            "STEP 9 — CTA TEXT (white, centered over pill, size=H*0.036)\n"
            "STEP 10 — BRAND MARK at top-left (x=W*0.06, y=H*0.06): a logo image or text mark\n"
            "STEP 11 — finalize_design\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  COLOR PALETTES\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "DARK CINEMATIC:  bg=#0a0a1a  accent=#c9a96e  text=#ffffff  sub=#b0b0b0\n"
            "BOLD ACTION:     bg=#0d0d0d  accent=#e63946  text=#ffffff  sub=#cccccc\n"
            "NEON TECH:       bg=#0a0a2e  accent=#00ff87  text=#ffffff  sub=#7f8c8d\n"
            "ROYAL LUXURY:    bg=#1a0a2e  accent=#9b59b6  gold=#f1c40f  text=#ffffff\n"
            "OCEAN COOL:      bg=#0c2340  accent=#00b4d8  text=#ffffff  sub=#90e0ef\n"
            "RIDE / MOBILITY: bg=#0e2233  accent=#ff7a00  pill=#ff7a00  text=#ffffff  sub=#e2e8f0\n"
            "FOOD / WARM:     bg=#2b1700  accent=#ffb01f  text=#ffffff  sub=#ffeac2\n"
            "FINTECH CLEAN:   bg=#0a1b2a  accent=#00d4ff  text=#ffffff  sub=#9bb0c4\n"
            "ECOM MINIMAL:    bg=#f5f1ec  accent=#1a1a1a  text=#1a1a1a  sub=#6e6e6e\n"
            "NEVER: yellow-on-cyan | bright-red-on-blue | neon-on-neon\n"
            "CONTRAST RULE: text and its background must have brightness difference ≥ 50%.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  PHOTO & COMPOSITING\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  add_image_layer(keyword)           → fills ENTIRE canvas — use for backgrounds\n"
            "  add_element_layer(kw,x,y,w,h)      → precise position — use for subjects/elements\n"
            "    remove_background=true           → AI mask to isolate subject\n"
            "  generate_fill(prompt,x,y,w,h)      → Photoshop Generative Fill (PS 2024+)\n"
            "BLEND MODES: 4=Multiply  7=Screen  11=Overlay  12=SoftLight  18=Difference  19=Exclusion\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  SCALING & MOVING\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "scale_layer: always uniform. To fit layer into box_w: scale_percent=(box_w/layer_w)*100\n"
            "move_layer:  delta_x/y are OFFSETS. To reach absolute pos: delta = target - current_left.\n"
            "rotate_layer: angle in degrees, positive=clockwise.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  COMMON MISTAKES — NEVER DO THESE\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✗ Placing text/shapes without checking for overlap\n"
            "✗ Using x=0, y=0 for text (always ≥50px margin from edges)\n"
            "✗ Stacking multiple background layers at 100% opacity\n"
            "✗ All text the same size — always vary for hierarchy (≥2× size gap)\n"
            "✗ More than 4 text layers — keep designs clean\n"
            "✗ Ignoring canvas size when calculating positions\n"
            "✗ Guessing positions — always CALCULATE using the zone/margin system\n"
            "✗ Flat single-layer backgrounds — always add an atmosphere layer for depth\n"
            "✗ CTA button without a colored pill behind it — the pill IS the button\n"
            "✗ Skipping the brand mark in the top-left corner — always include one\n"
            "✗ Mixing two display font families — one family, two weights MAX\n"
        )
        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

    def add_user_chat(self, msg, save_psd=False):
        self.save_psd = save_psd
        self.messages.append({"role": "user", "content": msg})

    # ── Layer map helper ──────────────────────────────────────────────

    def _format_layer_map(self, layer_context):
        """Build a clear text block mapping each layer index to its content and bounds."""
        resolution = layer_context.get("resolution", "unknown")
        fonts_used = layer_context.get("fonts_used", [])
        cw = layer_context.get("canvas_w", 1080)
        ch = layer_context.get("canvas_h", 1080)
        lines = [
            f"Canvas: {resolution}  ({cw}x{ch} px)",
            f"Fonts in document: {', '.join(fonts_used) if fonts_used else 'none detected'}",
            f"",
            f"LAYER MAP (index=use this number in tool calls):",
            f"{'─'*72}",
        ]
        for layer in layer_context.get("layers", []):
            idx   = layer.get("index", "?")
            name  = layer.get("name", "unnamed")
            kind  = layer.get("kind", "?")
            op    = layer.get("opacity", 100)
            bm    = layer.get("blend_mode", "Normal")
            vis   = "" if layer.get("visible", True) else " [HIDDEN]"
            b     = layer.get("bounds", {})

            # Bounds line
            if b:
                bounds_str = (
                    f"  pos=({b.get('left',0)},{b.get('top',0)}) "
                    f"size={b.get('width',0)}x{b.get('height',0)} "
                    f"center=({b.get('center_x',0)},{b.get('center_y',0)})"
                )
            else:
                bounds_str = ""

            header = f"[{idx:>3}] {kind:<12} '{name}'{vis}  op={op}%  blend={bm}"
            lines.append(header)
            if bounds_str:
                lines.append(bounds_str)

            # Text details
            if kind == "text":
                txt   = layer.get("text", "").replace("\n", "↵").replace("\r", "↵")
                fnt   = layer.get("font", "?")
                fsize = layer.get("font_size", "?")
                col   = layer.get("color_hex", "#?")
                align = layer.get("alignment", "left")
                tpos  = layer.get("text_position", "?")
                lead  = layer.get("leading", "auto")
                track = layer.get("tracking", 0)
                lines.append(
                    f"  TEXT: \"{txt}\"  font={fnt}  size={fsize}pt  "
                    f"color={col}  align={align}"
                )
                lines.append(
                    f"  text_pos={tpos}  leading={lead}  tracking={track}"
                )
            lines.append("")

        return "\n".join(lines)

    # ── Temp-file helper (writes to OS temp, not output folder) ──────

    def _get_preview_path(self):
        """Return a stable temp file path that gets reused/overwritten each capture."""
        return os.path.join(tempfile.gettempdir(), "desain_live_preview.png")

    def _capture_temp_preview(self):
        """Export a preview PNG to a temp file that will NOT pollute the output folder.
        The file is kept on disk so the UI can load it into the preview panel.
        Returns (file_path, base64_str) or (None, None) on failure."""
        temp_path = self._get_preview_path()
        if not self.ps_client.export_preview(temp_path):
            return None, None
        try:
            with open(temp_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            # Update live preview in the UI — file stays on disk so QPixmap can load it
            if self.preview_callback:
                self.preview_callback(temp_path)
            return temp_path, b64
        except Exception:
            return None, None

    # ── Internal Vision QA loop (runs before save) ───────────────────

    def _run_internal_vision_loop(self):
        """Run up to 4 rounds of vision QA and auto-fix before allowing save."""
        if not self.ps_client.psd:
            return
        self.log("[SYSTEM] Starting internal Vision QA check...")
        for iteration in range(4):
            self.log(f"[SYSTEM] Vision QA round {iteration + 1}/4 — capturing preview...")
            _, b64 = self._capture_temp_preview()
            if not b64:
                self.log("[SYSTEM] Could not capture preview, skipping QA.")
                break
            ctx = self.ps_client.get_layer_context()
            approved, updates = self.execute_vision_critique(b64, ctx, self.edit_log)
            if approved:
                self.log("[SYSTEM] QA check passed.")
                return
            # Apply each fix the vision agent requested
            for tool_name, args in updates:
                if tool_name == "move_layer":
                    self.ps_client.move_layer(
                        args.get("index", 0),
                        args.get("delta_x", 0),
                        args.get("delta_y", 0)
                    )
                    self.edit_log.append(f"[QA FIX] move_layer index={args.get('index',0)} dx={args.get('delta_x',0)} dy={args.get('delta_y',0)}")
                elif tool_name == "set_layer_properties":
                    self.ps_client.set_layer_properties(
                        args.get("index", 0),
                        args.get("text"),
                        args.get("font_size"),
                        args.get("opacity"),
                        args.get("blend_mode")
                    )
                    self.edit_log.append(f"[QA FIX] set_layer_properties index={args.get('index',0)} text={args.get('text')} font_size={args.get('font_size')}")
        self.log("[SYSTEM] QA loop exhausted max iterations.")

    # ── Main agent loop ──────────────────────────────────────────────

    def run_agent_loop(self, stop_flag=None):
        client = self._get_client()
        model_id = self.get_model()
        tools = self.get_tools()

        for turn in range(25):
            # Check stop flag before each LLM call
            if stop_flag and stop_flag():
                self.log("[SYSTEM] Task stopped by user.")
                return False

            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=self.messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.7,
                )
                message = response.choices[0].message
                self.messages.append(message)

                # ── No tool calls – just text ────────────────────────
                if not message.tool_calls:
                    if message.content:
                        self.log(f"[AGENT] {message.content}")
                    if turn > 5:
                        break
                    continue

                # ── Process tool calls ───────────────────────────────
                for tool_call in message.tool_calls:
                    fname = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    self.log(f"[AGENT: TOOL CALL] {fname}({args})")

                    result = "Error executing tool"

                    # ─── open_template ───────────────────────────────
                    if fname == "open_template":
                        filename = args.get("filename", "")
                        if filename and not filename.lower().endswith(".psd"):
                            filename += ".psd"
                        result = self.ps_client.open_document(
                            os.path.join(self.templates_folder, filename)
                        )
                        if result.startswith("Document opened"):
                            ctx = self.ps_client.get_layer_context()
                            # Deep vision – only once per unique template
                            if filename not in self.template_cache:
                                _, b64 = self._capture_temp_preview()
                                if b64:
                                    self.template_cache[filename] = self.analyze_template(b64, ctx)
                                else:
                                    self.template_cache[filename] = "Visual analysis unavailable."
                            analysis = self.template_cache[filename]
                            # Use the human-readable LAYER MAP (much easier for the LLM
                            # to parse than a raw JSON dump of the layer tree).
                            layer_map = self._format_layer_map(ctx)
                            result += (
                                f"\n\n--- Deep Visual Breakdown ---\n{analysis}"
                                f"\n\n--- {layer_map}"
                            )

                    # ─── create_canvas ────────────────────────────────
                    elif fname == "create_canvas":
                        result = self.ps_client.create_canvas(
                            args.get("width", 1080),
                            args.get("height", 1080),
                            args.get("filename", "scratch_design"),
                        )

                    # ─── save_document ────────────────────────────────
                    elif fname == "save_document":
                        out_name = args.get("filename", "saved_design")
                        result = self.ps_client.save_document(
                            self.output_folder, out_name, self.save_psd
                        )
                        if self.preview_callback:
                            self.preview_callback(
                                os.path.join(self.output_folder, f"{out_name}.png")
                            )

                    # ─── close_document ────────────────────────────────
                    elif fname == "close_document":
                        result = self.ps_client.close_document()
                        self.edit_log.clear()

                    # ─── add_image_layer (Unsplash) ──────────────────
                    elif fname == "add_image_layer":
                        keyword = args.get("keyword", "abstract")
                        img_path = get_image_from_unsplash(
                            keyword, self.output_folder, self.log
                        )
                        if img_path:
                            result = self.ps_client.add_image_layer(
                                img_path,
                                args.get("blend_mode", 1),
                                args.get("opacity", 100),
                            )
                            try: os.remove(img_path)
                            except: pass
                        else:
                            result = "Error: Failed to download image from Unsplash."

                    # ─── add_solid_color_layer ────────────────────────
                    elif fname == "add_solid_color_layer":
                        result = self.ps_client.add_solid_color_layer(
                            args.get("hex_color", "#000000"),
                            args.get("blend_mode", 1),
                            args.get("opacity", 100),
                        )

                    # ─── add_gradient_layer ────────────────────────────
                    elif fname == "add_gradient_layer":
                        result = self.ps_client.add_gradient_layer(
                            args.get("hex_color1", "#000000"),
                            args.get("hex_color2", "#333333"),
                            args.get("angle", 90),
                            args.get("opacity", 100),
                            args.get("blend_mode", 1),
                        )

                    # ─── add_shape ─────────────────────────────────────
                    elif fname == "add_shape":
                        shape_type = args.get("shape_type", "rectangle")
                        w = args.get("width", 200)
                        h = args.get("height", 100)
                        # 'circle' is a friendly alias for 'ellipse' with equal sides
                        if shape_type == "circle":
                            shape_type = "ellipse"
                            side = min(w, h)  # force square bounding box
                            w, h = side, side
                        result = self.ps_client.add_shape(
                            shape_type,
                            args.get("x", 0),
                            args.get("y", 0),
                            w,
                            h,
                            args.get("hex_color", "#FFFFFF"),
                            args.get("corner_radius", 0),
                            args.get("opacity", 100),
                            args.get("rotation", 0),
                        )

                    # ─── add_text_layer ───────────────────────────────
                    elif fname == "add_text_layer":
                        result = self.ps_client.add_text_layer(
                            args.get("content", "Text"),
                            args.get("font_size", 72),
                            args.get("hex_color", "#FFFFFF"),
                            args.get("x", 100),
                            args.get("y", 200),
                            args.get("blend_mode", 1),
                            args.get("opacity", 100),
                            args.get("font_name"),
                            args.get("alignment", "left"),
                            args.get("rotation", 0),
                            args.get("letter_spacing"),
                        )

                    # ─── set_layer_properties ─────────────────────────
                    elif fname == "set_layer_properties":
                        result = self.ps_client.set_layer_properties(
                            args.get("index", 0),
                            args.get("text"),
                            args.get("font_size"),
                            args.get("opacity"),
                            args.get("blend_mode"),
                            args.get("font_name"),
                            args.get("hex_color"),
                        )
                        edit_desc = f"set_layer_properties(index={args.get('index',0)}"
                        if args.get("text"): edit_desc += f", text=\"{args['text']}\""
                        if args.get("font_size"): edit_desc += f", font_size={args['font_size']}"
                        if args.get("font_name"): edit_desc += f", font_name={args['font_name']}"
                        if args.get("hex_color"): edit_desc += f", hex_color={args['hex_color']}"
                        edit_desc += ")"
                        self.edit_log.append(edit_desc)

                    # ─── move_layer ───────────────────────────────────
                    elif fname == "move_layer":
                        result = self.ps_client.move_layer(
                            args.get("index", 0),
                            args.get("delta_x", 0),
                            args.get("delta_y", 0),
                        )
                        self.edit_log.append(f"move_layer(index={args.get('index',0)}, dx={args.get('delta_x',0)}, dy={args.get('delta_y',0)})")

                    # ─── rotate_layer ─────────────────────────────────
                    elif fname == "rotate_layer":
                        result = self.ps_client.rotate_layer(
                            args.get("index", 0),
                            args.get("angle", 0),
                        )

                    # ─── scale_layer ──────────────────────────────────
                    elif fname == "scale_layer":
                        # Enforce uniform scaling to always preserve aspect ratio.
                        scale = args.get("scale_percent",
                                         args.get("scale_x",
                                         args.get("scale_y", 100)))
                        sx = args.get("scale_x")
                        sy = args.get("scale_y")
                        if sx is not None and sy is not None and sx != sy:
                            scale = (sx + sy) / 2
                            self.log(
                                f"[RULE] Non-uniform scale (x={sx}, y={sy}). "
                                f"Forcing uniform {scale:.1f}% to preserve aspect ratio."
                            )
                        result = self.ps_client.scale_layer(
                            args.get("index", 0),
                            scale,
                        )
                    # ─── add_stroke ───────────────────────────────────
                    elif fname == "add_stroke":
                        result = self.ps_client.add_stroke(
                            args.get("index", 0),
                            args.get("thickness", 2),
                            args.get("hex_color", "#FFFFFF"),
                        )

                    # --- change_shape_color ----------------------------------
                    elif fname == "change_shape_color":
                        result = self.ps_client.change_shape_color(
                            args.get("index", 0),
                            args.get("hex_color", "#FFFFFF"),
                        )

                    # ─── add_pill_cta (combo shape + centered text) ───
                    elif fname == "add_pill_cta":
                        result = self.ps_client.add_pill_cta(
                            args.get("text", "Shop Now"),
                            args.get("x", 100),
                            args.get("y", 100),
                            args.get("width", 400),
                            args.get("height", 120),
                            args.get("pill_color", "#ff7a00"),
                            args.get("text_color", "#ffffff"),
                            args.get("font_size"),
                            args.get("font_name"),
                            args.get("corner_radius"),
                        )

                    # ─── reorder_layer ────────────────────────────────
                    elif fname == "reorder_layer":
                        result = self.ps_client.reorder_layer(
                            args.get("index", 0),
                            args.get("new_index", 0),
                        )

                    # ─── select_subject_and_mask ──────────────────────
                    elif fname == "select_subject_and_mask":
                        result = self.ps_client.select_subject_and_mask(
                            args.get("index", 0),
                        )

                    # ─── add_element_layer (Unsplash element) ─────────
                    elif fname == "add_element_layer":
                        keyword = args.get("keyword", "object")
                        img_path = get_image_from_unsplash(
                            keyword, self.output_folder, self.log
                        )
                        if img_path:
                            result = self.ps_client.add_element_layer(
                                img_path,
                                args.get("x", 0),
                                args.get("y", 0),
                                args.get("width", 400),
                                args.get("height", 400),
                                args.get("remove_background", False),
                                args.get("blend_mode", 1),
                                args.get("opacity", 100),
                                args.get("rotation", 0),
                            )
                            try: os.remove(img_path)
                            except: pass
                        else:
                            result = "Error: Failed to download element image from Unsplash."

                    # ─── generate_fill (AI generative content) ────────
                    elif fname == "generate_fill":
                        result = self.ps_client.generate_fill(
                            args.get("prompt", ""),
                            args.get("x", 0),
                            args.get("y", 0),
                            args.get("width", 500),
                            args.get("height", 500),
                        )

                    # ─── finalize_design ──────────────────────────────
                    elif fname == "finalize_design":
                        if self.ps_client.psd:
                            self._run_internal_vision_loop()
                            # Auto-save on finalize
                            out_name = args.get("filename", "design_output")
                            self.ps_client.save_document(
                                self.output_folder, out_name, self.save_psd
                            )
                            if self.preview_callback:
                                self.preview_callback(
                                    os.path.join(self.output_folder, f"{out_name}.png")
                                )
                        self.edit_log.clear()
                        self.log(f"[AGENT] {args.get('message', 'Design finalized.')}")
                        return True

                    # Push result back into conversation
                    self.messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": fname,
                        "content": result,
                    })

            except Exception as e:
                self.log(f"[SYSTEM] Agent execution failed: {e}")
                break

        return True

    # ── Reference Image Recreation ────────────────────────────────────

    def _get_image_dimensions(self, image_path):
        """Read actual image dimensions from file without heavy dependencies."""
        import struct
        try:
            with open(image_path, 'rb') as f:
                header = f.read(32)
                # PNG
                if header[:8] == b'\x89PNG\r\n\x1a\n':
                    w, h = struct.unpack('>II', header[16:24])
                    return w, h
                # BMP
                if header[:2] == b'BM':
                    w, h = struct.unpack('<ii', header[18:26])
                    return w, abs(h)
                # JPEG — need to scan for SOF marker
                if header[:2] == b'\xff\xd8':
                    f.seek(0)
                    data = f.read()
                    i = 2
                    while i < len(data) - 9:
                        if data[i] != 0xFF:
                            i += 1
                            continue
                        marker = data[i + 1]
                        if marker in (0xC0, 0xC1, 0xC2):
                            h, w = struct.unpack('>HH', data[i + 5:i + 9])
                            return w, h
                        if marker == 0xD9:
                            break
                        length = struct.unpack('>H', data[i + 2:i + 4])[0]
                        i += length + 2
        except:
            pass
        # Fallback: try PIL
        try:
            from PIL import Image
            img = Image.open(image_path)
            w, h = img.size
            img.close()
            return w, h
        except:
            pass
        return None, None

    def analyze_reference_image(self, image_path):
        """Analyze a reference image with the vision model and return structured
        JSON describing every layer for pixel-accurate recreation."""
        self.log("[SYSTEM] Analyzing reference image for recreation...")
        client = self._get_client()
        model_id = self.get_model()

        with open(image_path, "rb") as f:
            img_bytes = f.read()
        b64 = base64.b64encode(img_bytes).decode("utf-8")

        ext = os.path.splitext(image_path)[1].lower()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "bmp": "image/bmp", "webp": "image/webp"}.get(ext.replace(".", ""), "image/png")

        # Read actual image dimensions
        actual_w, actual_h = self._get_image_dimensions(image_path)
        if actual_w and actual_h:
            self.log(f"[SYSTEM] Reference image resolution: {actual_w}x{actual_h}")

        analysis_prompt = (
            'You are a top-tier design-vision analyst. Decompose this image into editable layers '
            'with PIXEL-LEVEL precision. The goal is faithful recreation — wrong sizes, missing '
            'layers, or ignored rotations are FAILURES.\n\n'

            'GOLDEN RULES BEFORE YOU START:\n'
            '1. SCAN THE ENTIRE IMAGE TWICE before listing layers. Many designs hide subtle accents '
            '   (black bars behind text, faded watermark text in the background, tiny dot accents).\n'
            '2. HERO TEXT FILLS THE CANVAS. If you see text that takes up >50% of the canvas width '
            '   and >10% of the canvas height, it IS the hero — capture its huge size accurately.\n'
            '3. EACH VISUAL LINE OF TEXT IS A SEPARATE LAYER if styled differently (size, color, '
            '   weight). Otherwise it can be one layer with lineCount > 1.\n'
            '4. ACCENT RECTANGLES BEHIND TEXT (typographic punch bars, highlight boxes) MUST be '
            '   captured as separate "shape" layers with lower zIndex than the text on top of them.\n'
            '5. BACKGROUND WATERMARKS (huge faded repeated text behind the design) ARE LAYERS too — '
            '   capture them as "text" layers with lower opacity (0.15-0.3) and very high zIndex=1.\n'
            '6. TILTED / ROTATED ELEMENTS — measure the rotation angle visually. Use NEGATIVE for '
            '   counter-clockwise tilt (e.g. left edge raised). Output rotation as a SIGNED integer.\n\n'

            'COMPLEX BACKGROUND ELEMENTS: If the background contains complex elements like patterns, '
            'textures, or noisy/grainy fills that are deeply integrated into the background structure, '
            'do NOT detach them. Leave them as part of the background. BUT — clearly separate large '
            'watermark/repeated-text, distinct foreground objects, and any accent bars: those ARE layers.\n\n'

            'Return a JSON object with:\n'
            '- "backgroundDescription": HIGHLY detailed description of the background visual appearance '
            '(colors, gradients, textures, lighting, stylistic mood, environment). '
            'CRITICAL: Do NOT include or mention any text or typography in this description. '
            'The background must be described as a clean canvas devoid of words.\n'
            '- "backgroundColor": single hex color summarizing the dominant background fill (CRITICAL).\n'
            '- "canvasWidth": estimated width in pixels (e.g. 1080)\n'
            '- "canvasHeight": estimated height in pixels (e.g. 1080)\n'
            '- "layers": An array of layer objects, sorted from BACKGROUND (zIndex=0) to FOREGROUND.\n\n'

            'Each layer object MUST have:\n'
            '- "id": a unique string\n'
            '- "name": descriptive name (e.g. "Main Subject", "Headline GRAVAR")\n'
            '- "type": strictly one of "background", "object", "text", or "shape"\n'
            '- LOGOS & ICONS: classify as "object" — do NOT decompose into shapes.\n'
            '- ACCENT BARS / HIGHLIGHTS: classify as "shape" with the exact rotation angle.\n'
            '- BACKGROUND WATERMARK TEXT (the huge faded repeating text): classify as "text" with '
            '  opacity 0.15-0.3 and zIndex=1 (above background, below everything else).\n'
            '- "box": { "ymin": N, "xmin": N, "ymax": N, "xmax": N } as percentages (0-100) of canvas.\n'
            '  - Background box MUST be {"ymin":0,"xmin":0,"ymax":100,"xmax":100}.\n'
            '  - FOR OBJECTS: box encompasses the ENTIRE visible structure.\n'
            '  - FOR TEXT: tightly wrap the glyph block — exclude excess whitespace.\n'
            '  - FOR ROTATED ELEMENTS: the box is the UN-ROTATED bounding box. Rotation is applied '
            '    separately. NEVER inflate the box to cover the rotated rectangle.\n'
            '- "zIndex": integer layer depth. Background=0, watermark=1, hero photo=2, '
            '  accent bars=3, headline text=4, sub-text=5, foreground icons=6+.\n'
            '- "rotation": SIGNED degrees (-180 to 180). 0 = upright. Negative = counter-clockwise.\n'
            '- "opacity": 0.0 to 1.0. Default 1.0.\n'
            '- "blendMode": only if the layer visibly blends ("multiply","screen","overlay","difference").\n'
            '- "shadowEnabled","shadowColor","shadowBlur","shadowOffsetX","shadowOffsetY": optional.\n\n'

            'For "text" type, you MUST include:\n'
            '- "content": the actual text (read EVERY character; preserve case).\n'
            '- "lineCount": integer number of visible lines in this text block (1 if single-line).\n'
            '- "fontFamily": choose the closest match. PROFESSIONAL DESIGNS COMMONLY USE: '
            '  "Anton","Bebas Neue","Oswald","Impact","Arial Black" (bold condensed sans-serif hero), '
            '  "Montserrat","Inter","Poppins","Roboto" (clean sans-serif), '
            '  "Playfair Display","Lora" (elegant serif). If the text is BOLD and CONDENSED with '
            '  very tight letter spacing — choose Anton, Bebas Neue, or Oswald-Bold.\n'
            '- "color": EXACT hex of the GLYPH FILL. Look directly at the letters, NOT the background. '
            '  Common values: "#ffffff" (white), "#000000" (black), the brand accent. NEVER output '
            '  the background color as the text color.\n'
            '- "fontStyle": "normal" or "italic"\n'
            '- "fontWeight": "normal","bold","100"-"900". For CONDENSED HERO TEXT use "900" or "bold".\n'
            '- "letterSpacing": integer (-100 to 200). Bold condensed hero text usually has -25 to 0.\n'
            '- "textAlign": "left", "center", or "right"\n'
            '- "textCase": "uppercase","lowercase","title","mixed" — describes the original case used.\n'
            '- "fontSize": per-mille of canvas height. Formula: '
            '  (single_line_visual_height_in_pixels / canvas_height_in_pixels) * 1000. '
            '  CRITICAL: For multi-line text, use the SINGLE-LINE height, NOT the whole block height. '
            '  Example: 1080-tall canvas, one line of text spans 150px → fontSize=139.\n'
            '  HERO HEADLINES are usually 80-180 per-mille. Tiny captions 15-25 per-mille.\n\n'

            'For "shape" type, you MUST include:\n'
            '- "backgroundColor": hex color code\n'
            '- "borderRadius": CSS border radius ("0px","8px","50%")\n'
            '- "shapeOpacity": 0.0 to 1.0\n'
            '- "borderWidth": stroke width in pixels (0 if none)\n'
            '- "borderColor": hex color of stroke if present\n'
            '- For ACCENT BARS BEHIND TEXT: zIndex MUST be EXACTLY one less than the text on top.\n\n'

            'COMMON FAILURE MODES TO AVOID:\n'
            '* Merging multiple visually-distinct lines into one text box — DO NOT.\n'
            '* Ignoring small but important elements (dots, ticks, top labels, social handles).\n'
            '* Outputting tiny fontSize for hero text — measure the glyph cap height carefully.\n'
            '* Forgetting black/dark accent rectangles that sit BEHIND hero text.\n'
            '* Reporting bbox of a rotated shape — always report UN-rotated bbox + rotation angle.\n\n'

            'IMPORTANT: Respond ONLY with the raw JSON object. NO markdown, NO ```json fences. '
            'Extract every distinct element (up to 25 layers) to ensure NOTHING is skipped. '
            'Always include exactly one "background" layer.'
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": analysis_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }
        ]

        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.2,
            )
            analysis = response.choices[0].message.content
            self.log("[SYSTEM] Reference image analysis complete.")
            return analysis, b64, actual_w, actual_h
        except Exception as e:
            self.log(f"[SYSTEM] Reference image analysis failed: {e}")
            return None, b64, actual_w, actual_h

    def _parse_reference_json(self, raw_text):
        """Parse the JSON from the vision model, handling markdown wrappers."""
        text = raw_text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            first_newline = text.find("\n")
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            self.log(f"[SYSTEM] JSON parse failed: {e}")
            return None

    def _build_recreation_instructions(self, data, canvas_w, canvas_h):
        """Convert parsed JSON layer data into precise tool-call instructions."""
        lines = []
        bg_desc = data.get("backgroundDescription", "dark gradient background")
        bg_color_hex = data.get("backgroundColor")

        # Sort layers by zIndex so accent shapes precede the text that sits on them.
        layers = sorted(data.get("layers", []), key=lambda l: l.get("zIndex", 0))

        for step, layer in enumerate(layers, start=1):
            ltype = layer.get("type", "")
            box = layer.get("box", {})
            name = layer.get("name", "unnamed")
            rotation = int(round(float(layer.get("rotation", 0) or 0)))
            # Normalise rotation to signed range [-180, 180]
            if rotation > 180:
                rotation -= 360
            opacity = float(layer.get("opacity", 1.0) or 1.0)
            opacity_pct = max(1, min(100, int(round(opacity * 100))))
            blend = (layer.get("blendMode") or "normal").lower()
            blend_map = {"normal": 1, "multiply": 5, "screen": 7,
                         "overlay": 16, "darken": 4, "color-dodge": 8,
                         "difference": 18, "exclusion": 19, "soft-light": 12,
                         "softlight": 12, "hard-light": 13, "hardlight": 13}
            blend_int = blend_map.get(blend, 1)

            # Convert percentage box to pixels
            x = int(box.get("xmin", 0) / 100 * canvas_w)
            y = int(box.get("ymin", 0) / 100 * canvas_h)
            x2 = int(box.get("xmax", 100) / 100 * canvas_w)
            y2 = int(box.get("ymax", 100) / 100 * canvas_h)
            w = max(1, x2 - x)
            h = max(1, y2 - y)

            if ltype == "background":
                if bg_color_hex:
                    bg_action = f'add_solid_color_layer(hex_color="{bg_color_hex}")'
                else:
                    bg_action = f'add_solid_color_layer(hex_color="#101010")'
                lines.append(
                    f"STEP {step} — LAYER: Background — '{name}'\n"
                    f"  Description: {bg_desc}\n"
                    f"  PRIMARY ACTION: {bg_action}\n"
                    f"  FALLBACK 1: add_gradient_layer(hex_color1=..., hex_color2=..., angle=...)\n"
                    f"  FALLBACK 2: generate_fill(prompt=\"{bg_desc}\", x=0, y=0, "
                    f"width={canvas_w}, height={canvas_h})\n"
                    f"  CRITICAL: Try fallbacks ONLY if the primary action returns an error.\n"
                )

            elif ltype == "object":
                # If the object is an isolated subject (hand, person, product), bg-removal helps.
                rb = "true"
                # Headphone/logo objects can be assumed to need bg-removal too.
                rotation_arg = f", rotation={rotation}" if rotation else ""
                lines.append(
                    f"STEP {step} — LAYER: Object — '{name}'\n"
                    f"  Position: x={x}, y={y}, width={w}, height={h}\n"
                    f"  Blend: {blend}({blend_int}), Opacity: {opacity_pct}%, Rotation: {rotation}°\n"
                    f"  ACTION: add_element_layer(keyword=\"{name}\", x={x}, y={y}, "
                    f"width={w}, height={h}, remove_background={rb}, "
                    f"blend_mode={blend_int}, opacity={opacity_pct}{rotation_arg})\n"
                )

            elif ltype == "text":
                content = (layer.get("content") or "").replace('"', '\\"')
                color = layer.get("color", "#FFFFFF")
                font = layer.get("fontFamily", "Arial")
                weight = layer.get("fontWeight", "bold")
                align = (layer.get("textAlign", "center") or "center").lower()
                spacing = int(layer.get("letterSpacing", 0) or 0)
                line_count = max(1, int(layer.get("lineCount", 1) or 1))
                case = (layer.get("textCase") or "mixed").lower()

                # ── Font size: prefer the vision model's per-mille value, sanity-checked
                # against the geometry of the bounding box.
                ai_font_pt = int(round(float(layer.get("fontSize", 0) or 0) / 1000.0 * canvas_h))
                # Geometry estimate: bbox height divided by lines, adjusted for
                # cap-height vs em ratio (~0.95 for sans, slightly higher for condensed).
                geo_font_pt = int(round((h / line_count) * 1.05))
                if ai_font_pt > 12 and geo_font_pt > 12:
                    # Use the LARGER of the two — vision models routinely underestimate.
                    font_pt = max(ai_font_pt, geo_font_pt)
                elif ai_font_pt > 12:
                    font_pt = ai_font_pt
                else:
                    font_pt = geo_font_pt
                font_pt = max(12, font_pt)

                # Map weight + family to a sensible PostScript-style hint for Photoshop.
                font_hint = font
                w_str = str(weight).lower()
                is_bold = w_str in ("bold", "700", "800", "900", "black", "heavy")
                if is_bold and "bold" not in font_hint.lower() and "black" not in font_hint.lower():
                    font_hint = f"{font}-Bold"

                # y for add_text_layer is the BASELINE. Place the baseline at the
                # bottom of the bounding box of the LAST line of text.
                # baseline_y ≈ bottom_of_box - descent (~20% of font size)
                text_y = y2 - int(font_pt * 0.15)

                if align == "center":
                    text_x = (x + x2) // 2
                elif align == "right":
                    text_x = x2
                else:
                    text_x = x

                # Recase the content if the analyst noted a case difference.
                emit_content = content
                if case == "uppercase":
                    emit_content = content.upper()
                elif case == "lowercase":
                    emit_content = content.lower()

                rotation_arg = f", rotation={rotation}" if rotation else ""
                spacing_arg = f", letter_spacing={spacing}" if spacing else ""
                font_arg = f", font_name=\"{font_hint}\"" if font_hint and font_hint != "Arial" else ""

                lines.append(
                    f"STEP {step} — LAYER: Text — '{name}'\n"
                    f"  Content: \"{emit_content}\"  (lines={line_count}, case={case})\n"
                    f"  Font: {font_hint} weight={weight}  Size: {font_pt}pt  "
                    f"(vision={ai_font_pt}pt, geometry={geo_font_pt}pt)\n"
                    f"  Color: {color}  ← USE THIS EXACT HEX\n"
                    f"  Box(px): x={x} y={y} w={w} h={h}   Baseline: y={text_y}\n"
                    f"  Align: {align}   Opacity: {opacity_pct}%   Rotation: {rotation}°\n"
                    f"  ACTION: add_text_layer(content=\"{emit_content}\", font_size={font_pt}, "
                    f"hex_color=\"{color}\", x={text_x}, y={text_y}, alignment=\"{align}\", "
                    f"opacity={opacity_pct}{rotation_arg}{spacing_arg}{font_arg})\n"
                )

            elif ltype == "shape":
                bg_color = layer.get("backgroundColor", "#000000")
                border_r = layer.get("borderRadius", "0px")
                shape_opacity = float(layer.get("shapeOpacity", 1.0) or 1.0)
                border_w = int(layer.get("borderWidth", 0) or 0)
                border_c = layer.get("borderColor", "#000000")

                corner = 0
                if isinstance(border_r, str):
                    if "50%" in border_r:
                        corner = min(w, h) // 2
                    else:
                        try:
                            corner = int(border_r.replace("px", "").strip())
                        except Exception:
                            corner = 0

                shape_type = "ellipse" if corner >= min(w, h) // 2 and w == h else "rectangle"
                s_opacity = max(1, min(100, int(round(shape_opacity * 100))))

                rotation_arg = f", rotation={rotation}" if rotation else ""
                lines.append(
                    f"STEP {step} — LAYER: Shape — '{name}'\n"
                    f"  Type: {shape_type}  Box: x={x} y={y} w={w} h={h}\n"
                    f"  Color: {bg_color}   Corner: {corner}px   Opacity: {s_opacity}%   "
                    f"Rotation: {rotation}°\n"
                    f"  ACTION: add_shape(shape_type=\"{shape_type}\", x={x}, y={y}, "
                    f"width={w}, height={h}, hex_color=\"{bg_color}\", "
                    f"corner_radius={corner}, opacity={s_opacity}{rotation_arg})\n"
                )
                if border_w > 0:
                    lines.append(
                        f"  THEN: add_stroke(index=-1, thickness={border_w}, "
                        f"hex_color=\"{border_c}\")  # -1 = last added layer\n"
                    )

            if layer.get("shadowEnabled"):
                sc = layer.get("shadowColor", "#000000")
                lines.append(
                    f"  SHADOW: color={sc}, blur={layer.get('shadowBlur', 5)}, "
                    f"offset=({layer.get('shadowOffsetX', 3)},"
                    f"{layer.get('shadowOffsetY', 3)})\n"
                )

            lines.append("")

        return "\n".join(lines)

    def init_reference_session(self, image_path, user_note, available_templates, save_psd=False):
        """Initialize a session specifically for recreating a reference image."""
        self.save_psd = save_psd
        analysis_raw, b64, actual_w, actual_h = self.analyze_reference_image(image_path)

        if not analysis_raw:
            self.init_session(user_note, available_templates, save_psd)
            return

        # Try to parse structured JSON
        parsed = self._parse_reference_json(analysis_raw)

        if parsed:
            # Use ACTUAL image dimensions (from file header), NOT the AI's estimate
            if actual_w and actual_h:
                canvas_w = actual_w
                canvas_h = actual_h
            else:
                canvas_w = parsed.get("canvasWidth", 1080)
                canvas_h = parsed.get("canvasHeight", 1080)

            instructions = self._build_recreation_instructions(parsed, canvas_w, canvas_h)

            recreation_prompt = (
                f"REFERENCE IMAGE RECREATION TASK\n\n"
                f"User instruction: {user_note}\n\n"
                f"Canvas: {canvas_w} x {canvas_h} (EXACT resolution from the reference image)\n\n"
                f"Below is a PRECISE LAYER-BY-LAYER BREAKDOWN, pre-sorted from background to\n"
                f"foreground. Every ACTION line is a ready-to-execute tool call.\n\n"
                f"--- LAYER INSTRUCTIONS ---\n{instructions}\n"
                f"--- END INSTRUCTIONS ---\n\n"
                f"EXECUTION CHECKLIST:\n"
                f"1. create_canvas(width={canvas_w}, height={canvas_h}, filename=\"recreation\")\n"
                f"2. For each STEP in order, execute its ACTION as a tool call. Copy-paste the\n"
                f"   exact parameter values (font_size, hex_color, x, y, alignment, rotation).\n"
                f"3. Use the EXACT x, y, width, height — they are already in pixels.\n"
                f"4. Use the EXACT hex_color from each ACTION — NEVER default to white.\n"
                f"5. Use the EXACT alignment (center/left/right).\n"
                f"6. PASS rotation= as a parameter to add_text_layer/add_shape/add_element_layer\n"
                f"   when the ACTION specifies it. Do NOT make a separate rotate_layer call.\n"
                f"7. Hero text font_sizes are LARGE on purpose — DO NOT shrink them.\n"
                f"8. Do NOT skip any STEP. Do NOT improvise extra layers.\n"
                f"9. Call finalize_design(filename=\"recreation\") when all STEPS are placed.\n"
            )
        else:
            # Fallback: use raw text analysis
            if actual_w and actual_h:
                canvas_w, canvas_h = actual_w, actual_h
            else:
                canvas_w, canvas_h = 1080, 1080
            recreation_prompt = (
                f"REFERENCE IMAGE RECREATION TASK\n\n"
                f"User instruction: {user_note}\n\n"
                f"Canvas: {canvas_w} x {canvas_h}\n\n"
                f"Below is a DETAILED ANALYSIS of the reference image.\n"
                f"Recreate this design as ACCURATELY as possible.\n\n"
                f"--- ANALYSIS ---\n{analysis_raw}\n--- END ---\n\n"
                f"Execute the recreation step by step. Do NOT improvise."
            )

        system_prompt = (
            "You are an elite-level Creative Director recreating a reference design in Photoshop.\n"
            "You have been given PIXEL-ACCURATE layer instructions derived from analyzing the reference.\n"
            "Your job is to execute each tool call EXACTLY as specified — treat them as copy-paste commands.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  EXECUTION ORDER (NEVER VIOLATE)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "1. The STEPS are pre-sorted by zIndex. Execute them in numerical order:\n"
            "   STEP 1, STEP 2, STEP 3, ... — NEVER skip ahead, NEVER reorder.\n"
            "2. Background is ALWAYS placed first. Foreground icons are placed last.\n"
            "3. Accent shapes (black bars behind text) MUST be placed BEFORE the text on top.\n"
            "4. Background watermark text (faded huge text behind the design) MUST be placed\n"
            "   AFTER the background but BEFORE the hero subject.\n"
            "5. Call finalize_design only when ALL steps are done.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  POSITIONING RULES\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "- All coordinates are already in PIXELS for the target canvas. Use them directly.\n"
            "- For add_text_layer: y = text BASELINE (the line glyphs sit on).\n"
            "- For center-aligned text: x = CENTER POINT of the text.\n"
            "- For right-aligned text:  x = RIGHT EDGE of the text.\n"
            "- For left-aligned text:   x = LEFT EDGE of the text.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  COLOR RULES (CRITICAL)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "- Each text layer has a specific hex_color in its ACTION — use it EXACTLY.\n"
            "- NEVER default text to white (#FFFFFF) unless the ACTION explicitly says #FFFFFF.\n"
            "- Copy the hex_color directly from the ACTION line.\n"
            "- For SHAPE layers: copy the hex_color from the ACTION — never guess.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ROTATION RULES (CRITICAL)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "- add_text_layer, add_shape, add_element_layer ALL accept a `rotation` parameter.\n"
            "- If the ACTION includes `rotation=N`, PASS IT through. Do NOT make a separate\n"
            "  rotate_layer call — rotation is baked into the creation tool call.\n"
            "- Positive rotation = clockwise. Negative = counter-clockwise.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  TYPOGRAPHY RULES (CRITICAL — fixes shrunken text)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "- The font_size in each ACTION is in POINTS and IS ACCURATE. Do NOT reduce it.\n"
            "- Hero headlines often have font_size > 150pt. That is INTENTIONAL — keep it.\n"
            "- If the ACTION specifies font_name, pass it through. For BOLD CONDENSED hero\n"
            "  text, valid font names include 'Anton-Regular','BebasNeue-Regular','Oswald-Bold',\n"
            "  'Impact','Arial-Black'. Try several in order if the first is missing.\n"
            "- letter_spacing: if the ACTION specifies it, pass it through. Negative values\n"
            "  create the tight letter-spacing common in condensed hero fonts.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  CONTENT RULES (CRITICAL — fixes wrong-case text)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "- Copy the `content=\"...\"` string from each ACTION character-by-character.\n"
            "- Preserve case EXACTLY. If the ACTION says \"GRAVAR\" do not lowercase it.\n"
            "- Preserve special characters (accents, ñ, ã, ç).\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ALIGNMENT RULES\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "- Each text ACTION includes alignment='center'|'left'|'right'. ALWAYS pass it.\n"
            "- Do NOT omit the alignment parameter.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  SCALING RULES (ABSOLUTE)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "- ALWAYS preserve aspect ratio when scaling. Use a single uniform scale_percent.\n"
            "- Distorted/stretched layers are UNACCEPTABLE.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ABSOLUTE DON'Ts\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "* Do NOT skip any STEP — every layer matters, including small accents.\n"
            "* Do NOT shrink hero text below what the ACTION specifies.\n"
            "* Do NOT merge multiple text layers into one — keep each STEP separate.\n"
            "* Do NOT call rotate_layer or scale_layer unless explicitly required as a follow-up.\n"
            "* Do NOT call close_document unless the user explicitly asks.\n"
            "* Do NOT improvise extra layers that aren't in the instructions.\n"
        )

        new_msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": recreation_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }
        
        if not self.messages:
            self.messages = [
                {"role": "system", "content": system_prompt},
                new_msg
            ]
        else:
            # Update the system prompt (always index 0) and append the new task
            if self.messages[0].get("role") == "system":
                self.messages[0]["content"] = system_prompt
            else:
                self.messages.insert(0, {"role": "system", "content": system_prompt})
            self.messages.append(new_msg)

    # ── Deep visual analysis (first open only) ───────────────────────

    def analyze_template(self, base64_image, layer_context):
        self.log("[SYSTEM] Sending template for Deep Vision Analysis...")
        client = self._get_client()
        model_id = self.get_model()

        layer_map = self._format_layer_map(layer_context)

        system_prompt = (
            "You are an expert Design Analyst. You are looking at a freshly opened PSD template.\n"
            "Provide a 'Deep Structural Breakdown' for the editing agent.\n\n"
            "Below is the EXACT layer structure with indexes. Use these indexes when referencing layers:\n"
            f"{layer_map}\n\n"
            "Identify and describe IN DETAIL:\n"
            "1. HEADLINE: Which layer index? How many lines does it span? Current text content. "
            "Note its font size as a % of canvas height — this tells the editor the headline scale.\n"
            "2. CTA (Call To Action): Which layer index? Is it inside a pill / rounded rectangle? "
            "If yes, name BOTH the text layer index AND the pill shape index. State the corner "
            "the pill is anchored to (bottom-right, top-right, etc.). Current text + max char length.\n"
            "3. BODY / SUB-TEXT: Which layer indexes? Their positions and line counts.\n"
            "4. ACCENT SHAPES: Any rectangles sitting BEHIND text for typographic punch? List their\n"
            "   indexes and the text layer they accompany.\n"
            "5. HERO SUBJECT: Which layer is the dominant photo/illustration? Its bounding-box "
            "as % of canvas (e.g. \"y=31%-86%, ~55% of canvas height\").\n"
            "6. BRAND MARK / LOGO: Is there a logo in the top-left corner? Which index? Its size?\n"
            "7. SECONDARY ICONS: Any download / app-store icons or footer marks? Which indexes?\n"
            "8. TONE OF VOICE (TOV): What is the vibe? Professional, playful, urgent, luxurious?\n"
            "9. SHAPE CONSTRAINTS: Are any text layers inside shapes (rounded rectangles, circles, "
            "banners)? If so, note which index and the max text length that fits.\n"
            "10. LAYOUT ZONES: Describe the visual hierarchy. Which corner anchors the CTA? "
            "Which corner anchors the brand? Where is the eye drawn first?\n"
            "11. COLOR DNA: List every distinct color (background, accent, text, pill) as hex.\n"
            "12. BLEED ELEMENTS: List any layers whose bounds extend past the canvas edges — these "
            "are intentional pro-design bleeds.\n\n"
            "IMPORTANT: Always reference layers by their [Index N] so the editing agent knows exactly "
            "which layer to modify. Read each text from the image and verify it matches the layer data."
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": system_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                ],
            }
        ]

        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.5,
            )
            analysis = response.choices[0].message.content
            self.log("[SYSTEM] Deep Vision Analysis complete.")
            return analysis
        except Exception as e:
            self.log(f"[SYSTEM] Deep Vision Analysis failed: {e}")
            return "Visual analysis failed. Rely on layer names only."

    # ── Vision QA critique ───────────────────────────────────────────

    def execute_vision_critique(self, base64_image, layer_context, edits_made=None):
        self.log("[SYSTEM] Submitting to Vision Agent for critique...")
        client = self._get_client()
        model_id = self.get_model()

        vision_tools = [
            {
                "type": "function",
                "function": {
                    "name": "approve_design",
                    "description": "Call ONLY if the design passes ALL quality checks with zero issues.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_layer_properties",
                    "description": "Fix a layer – change text, font_size, opacity, or blend_mode.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer"},
                            "text": {"type": "string"},
                            "font_size": {"type": "integer"},
                            "opacity": {"type": "integer"},
                            "blend_mode": {"type": "integer"}
                        },
                        "required": ["index"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "move_layer",
                    "description": "Move a layer by pixel offsets to fix positioning.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer"},
                            "delta_x": {"type": "integer"},
                            "delta_y": {"type": "integer"}
                        },
                        "required": ["index", "delta_x", "delta_y"]
                    }
                }
            }
        ]

        layer_map = self._format_layer_map(layer_context)

        # Build edits summary
        edits_section = ""
        if edits_made:
            edits_section = (
                "\n\n=== EDITS THAT WERE MADE (verify each one) ===\n"
                + "\n".join(f"  • {e}" for e in edits_made)
                + "\n=== END OF EDITS ==="
            )

        # Build expected-text verification list
        text_verification = "\n\n=== TEXT VERIFICATION CHECKLIST ===\n"
        for layer in layer_context.get("layers", []):
            if layer.get("type") == "text":
                idx = layer.get("index", "?")
                expected = layer.get("text", "")
                text_verification += f"  [Index {idx}] Expected FULL text: \"{expected}\"\n"
        text_verification += (
            "For EACH text layer above, READ the actual text visible in the image.\n"
            "If you cannot read the FULL expected text (some characters are missing, cut off, "
            "or only a portion is visible), that text is CROPPED or EXCEEDING the canvas.\n"
            "=== END CHECKLIST ==="
        )

        system_prompt = (
            "You are a strict Vision QA Director. Review the provided design screenshot.\n\n"
            f"=== LAYER MAP (use these indexes for any fixes) ===\n{layer_map}\n"
            f"{edits_section}"
            f"{text_verification}\n\n"
            "CHECK EACH of the following — do NOT skip any:\n"
            "1. TEXT COMPLETENESS: For every text layer, read the FULL text from the image. "
            "Compare it against the expected text above. If ANY characters are missing or the text "
            "appears truncated/cropped, it FAILS. Fix by reducing font_size or shortening text.\n"
            "2. READABILITY & CONTRAST: Is every text element clearly legible?\n"
            "3. CTA PROMINENCE: Is the Call To Action visually dominant?\n"
            "4. SHAPE OVERFLOW: Has any text spilled outside a button, badge, or banner?\n"
            "5. CANVAS BOUNDARIES: Is any element cut off at any edge?\n"
            "6. MULTI-LINE BALANCE: If text spans multiple lines, is it balanced?\n\n"
            "RULES:\n"
            "- If EVERYTHING passes, call 'approve_design'.\n"
            "- If ANY check fails, call 'set_layer_properties' or 'move_layer' to fix it.\n"
            "- NEVER approve a design with cropped, overlapping, or unreadable text.\n"
            "- Always reference layers by their [Index N].\n"
            "- If text is cropped: REDUCE font_size or SHORTEN text.\n"
            "- If text is off-canvas: use move_layer to bring it inward."
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": system_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                ],
            }
        ]

        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                tools=vision_tools,
                tool_choice="auto",
                temperature=0.3,
            )

            message = response.choices[0].message
            if message.tool_calls:
                updates = []
                for tc in message.tool_calls:
                    fn = tc.function.name
                    if fn == "approve_design":
                        self.log("[SYSTEM] Vision Agent approved the design.")
                        return True, []
                    else:
                        tc_args = json.loads(tc.function.arguments)
                        self.log(f"[VISION: TOOL CALL] {fn}({tc_args})")
                        updates.append((fn, tc_args))
                return False, updates
            else:
                self.log("[SYSTEM] Vision agent returned no tool calls. Assuming approved.")
                return True, []
        except Exception as e:
            self.log(f"[SYSTEM] Vision API failed: {e}")
            return True, []
