import os
import math
import time
import win32com.client as win32


class PhotoshopClient:
    def __init__(self, log_callback=None):
        self.log = log_callback or print
        self.app = None
        self.psd = None
        self._doc_name = None

    def connect(self):
        self.log("[INFO] Connecting to Photoshop COM Interface...")
        self.app = win32.Dispatch('Photoshop.Application')
        try:
            self.app.DisplayDialogs = 3  # psDisplayNoDialogs
        except:
            pass

    def disconnect(self):
        if self.psd:
            try:
                self.psd.Close(2)
            except:
                pass

    # ── Internal helpers ─────────────────────────────────────────────

    def _ensure_active(self):
        """Ensure our target document is valid and active."""
        if not self.app:
            return False
        if self.psd:
            try:
                _ = self.psd.Name
                self.app.ActiveDocument = self.psd
                return True
            except:
                pass
        if self._doc_name:
            try:
                for i in range(1, self.app.Documents.Count + 1):
                    doc = self.app.Documents.Item(i)
                    if doc.Name == self._doc_name:
                        self.psd = doc
                        self.app.ActiveDocument = doc
                        return True
            except:
                pass
        try:
            if self.app.Documents.Count > 0:
                self.psd = self.app.ActiveDocument
                self._doc_name = self.psd.Name
                return True
        except:
            pass
        return False

    def _close_all_except_ours(self):
        try:
            if not self.app or not self._doc_name:
                return
            docs_to_close = []
            for i in range(1, self.app.Documents.Count + 1):
                doc = self.app.Documents.Item(i)
                if doc.Name != self._doc_name:
                    docs_to_close.append(doc)
            for doc in docs_to_close:
                try:
                    doc.Close(2)
                except:
                    pass
        except:
            pass

    def _safe_set_blend_opacity(self, layer, blend_mode, opacity):
        try:
            if blend_mode is not None and blend_mode != 1:
                layer.BlendMode = blend_mode
        except:
            pass
        try:
            if opacity is not None and opacity != 100:
                layer.Opacity = opacity
        except:
            pass

    def _safe_get_index(self, layer):
        try:
            return self._get_layer_index(layer)
        except:
            return -1

    def _get_bounds(self, layer):
        try:
            b = layer.Bounds
            left, top, right, bottom = int(b[0]), int(b[1]), int(b[2]), int(b[3])
            return {"left": left, "top": top, "right": right, "bottom": bottom,
                    "width": right - left, "height": bottom - top}
        except:
            return "unknown"

    def _get_canvas_size(self):
        try:
            return int(self.psd.Width), int(self.psd.Height)
        except:
            return 1080, 1080

    def _auto_fix_bounds(self, layer):
        """If a layer extends beyond the canvas, translate it back inside."""
        try:
            cw, ch = self._get_canvas_size()
            b = layer.Bounds
            left, top, right, bottom = int(b[0]), int(b[1]), int(b[2]), int(b[3])
            lw, lh = right - left, bottom - top
            margin = 10
            dx, dy = 0, 0

            # Fix horizontal
            if lw >= cw - 2 * margin:
                # Layer wider than canvas — center it
                dx = (cw // 2) - (left + lw // 2)
            elif left < margin:
                dx = margin - left
            elif right > cw - margin:
                dx = (cw - margin) - right

            # Fix vertical
            if lh >= ch - 2 * margin:
                dy = (ch // 2) - (top + lh // 2)
            elif top < margin:
                dy = margin - top
            elif bottom > ch - margin:
                dy = (ch - margin) - bottom

            if dx != 0 or dy != 0:
                layer.Translate(dx, dy)
        except:
            pass

    def _get_layer_index(self, target_layer):
        all_layers = self.get_all_layers()
        for i, layer in enumerate(all_layers):
            try:
                if layer.Name == target_layer.Name:
                    return i
            except:
                pass
        return -1

    def get_all_layers(self, psd_layers=None):
        if psd_layers is None:
            if not self.psd:
                return []
            try:
                psd_layers = self.psd.Layers
            except:
                return []
        layers_list = []
        for layer in psd_layers:
            try:
                layers_list.append(layer)
            except:
                pass
            try:
                sub = layer.Layers
                if sub and sub.Count > 0:
                    layers_list.extend(self.get_all_layers(sub))
            except:
                pass
        return layers_list

    def _hex_to_rgb(self, hex_color):
        c = str(hex_color).strip().replace("#", "").lower()
        # Common color name fallback
        names = {
            "red": "ff0000", "green": "00ff00", "blue": "0000ff",
            "white": "ffffff", "black": "000000", "yellow": "ffff00",
            "orange": "ff8c00", "purple": "800080", "pink": "ff69b4",
            "cyan": "00ffff", "gold": "ffd700", "silver": "c0c0c0",
            "grey": "808080", "gray": "808080", "magenta": "ff00ff",
            "teal": "008080", "navy": "000080", "maroon": "800000",
            "lime": "00ff00", "brown": "8b4513", "coral": "ff7f50",
            "crimson": "dc143c", "indigo": "4b0082", "turquoise": "40e0d0",
            "salmon": "fa8072", "khaki": "f0e68c", "beige": "f5f5dc",
        }
        if c in names:
            c = names[c]
        # Handle 3-char shorthand (#f0a → ff00aa)
        if len(c) == 3:
            c = c[0]*2 + c[1]*2 + c[2]*2
        # Pad if too short
        c = c.ljust(6, "0")[:6]
        try:
            return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        except ValueError:
            return 255, 255, 255  # fallback to white

    def _normalize_hex(self, hex_color):
        """Convert any color input to a clean 6-char hex string for Photoshop HexValue."""
        r, g, b = self._hex_to_rgb(hex_color)
        return f"{r:02x}{g:02x}{b:02x}"

    # ── Document operations ──────────────────────────────────────────

    def create_canvas(self, width, height, filename):
        self.log(f"[INFO] Creating new canvas: {width}x{height} for {filename}")
        self.psd = self.app.Documents.Add(width, height, 72, filename, 2)
        self._doc_name = self.psd.Name
        time.sleep(0.3)
        return f"Canvas created successfully. Resolution: {width}x{height}."

    def open_document(self, path):
        self.log(f"[INFO] Opening document: {path}")
        self.psd = self.app.Open(path)
        self._doc_name = self.psd.Name
        time.sleep(0.3)
        return "Document opened successfully."

    def close_document(self):
        try:
            if not self.psd:
                return "No active document to close."
            self.psd.Close(2)
            self.psd = None
            self._doc_name = None
            return "Document closed without saving."
        except Exception as e:
            return f"Error closing document: {e}"

    def save_document(self, output_folder, filename, save_psd=False):
        """Export PNG (and optionally PSD) WITHOUT closing the document."""
        try:
            if not self.psd:
                return "No active document."
            self._ensure_active()
            png_path = os.path.join(output_folder, f"{filename}.png")
            self.export_preview(png_path)
            if save_psd:
                psd_path = os.path.join(output_folder, f"{filename}.psd")
                self.psd.SaveAs(psd_path)
            return f"Saved as {filename}.png (document still open for further edits)."
        except Exception as e:
            self.log(f"[ERROR] Failed to save: {e}")
            return f"Error saving: {e}"

    # ── Layer: Image ─────────────────────────────────────────────────

    def add_image_layer(self, image_path, blend_mode=1, opacity=100):
        try:
            self._ensure_active()
            psd_width, psd_height = self._get_canvas_size()

            if not os.path.exists(image_path) or os.path.getsize(image_path) < 1000:
                return f"Error: Image file is missing or too small."

            background_doc = self.app.Open(image_path)
            time.sleep(0.2)

            bg_w = int(background_doc.Width)
            bg_h = int(background_doc.Height)
            psd_ratio = psd_width / psd_height
            bg_ratio = bg_w / bg_h

            if bg_ratio > psd_ratio:
                new_w, new_h = int(bg_h * psd_ratio), bg_h
            else:
                new_w, new_h = bg_w, int(bg_w / psd_ratio)

            background_doc.ResizeCanvas(new_w, new_h)
            background_doc.ResizeImage(psd_width, psd_height)
            background_doc.Selection.SelectAll()
            background_doc.Selection.Copy()
            background_doc.Close(2)

            self._ensure_active()
            time.sleep(0.1)
            self.psd.Paste()
            time.sleep(0.1)

            layer = self.psd.ActiveLayer
            self._safe_set_blend_opacity(layer, blend_mode, opacity)
            idx = self._safe_get_index(layer)
            bounds = self._get_bounds(layer)
            return f"Image layer added successfully at index {idx}. Bounds: {bounds}"
        except Exception as e:
            self.log(f"[ERROR] Failed to insert image layer: {e}")
            self._close_all_except_ours()
            self._ensure_active()
            return f"Error adding image layer: {e}"

    # ── Layer: Element Image (positioned, sized, optional bg removal) ─

    def add_element_layer(self, image_path, x, y, width, height,
                          remove_bg=False, blend_mode=1, opacity=100, rotation=0):
        """Place an image at a specific position and size. Optionally remove background."""
        try:
            self._ensure_active()
            if not os.path.exists(image_path) or os.path.getsize(image_path) < 1000:
                return "Error: Image file is missing or too small."

            # Open the image in a temp document
            img_doc = self.app.Open(image_path)
            time.sleep(0.2)

            # ── Aspect-ratio-preserving resize ───────────────────────
            # Fit image INSIDE the target box without distorting it.
            orig_w = int(img_doc.Width)
            orig_h = int(img_doc.Height)

            if orig_w > 0 and orig_h > 0:
                scale_w = width  / orig_w
                scale_h = height / orig_h
                # Use the smaller scale so the image fits inside the box
                scale = min(scale_w, scale_h)
                fit_w = max(1, int(orig_w * scale))
                fit_h = max(1, int(orig_h * scale))
            else:
                fit_w, fit_h = width, height

            img_doc.ResizeImage(fit_w, fit_h)
            img_doc.Selection.SelectAll()
            img_doc.Selection.Copy()
            img_doc.Close(2)  # close without saving

            # Paste into main document
            self._ensure_active()
            time.sleep(0.1)
            self.psd.Paste()
            time.sleep(0.1)

            layer = self.psd.ActiveLayer
            try:
                layer.Name = "Element"
            except:
                pass

            # ── Move to target position ───────────────────────────────
            # Center the (possibly smaller-than-box) image inside the target box
            try:
                b = layer.Bounds
                curr_left, curr_top = float(b[0]), float(b[1])
                curr_w = float(b[2]) - curr_left
                curr_h = float(b[3]) - float(b[1])
                # Place top-left of the image at (x, y) — the caller provides the top-left corner
                target_left = float(x)
                target_top  = float(y)
                dx = target_left - curr_left
                dy = target_top  - curr_top
                layer.Translate(dx, dy)
            except:
                pass

            # ── Safety clamp: keep image visible on canvas ────────────
            try:
                cw, ch = self._get_canvas_size()
                b2 = layer.Bounds
                img_left  = float(b2[0])
                img_top   = float(b2[1])
                img_right = float(b2[2])
                img_bot   = float(b2[3])
                clamp_dx, clamp_dy = 0.0, 0.0
                # If entirely off right edge, pull left
                if img_left >= cw:
                    clamp_dx = cw - img_right - 10
                # If entirely off left edge, pull right
                elif img_right <= 0:
                    clamp_dx = -img_left + 10
                # If entirely off bottom edge, pull up
                if img_top >= ch:
                    clamp_dy = ch - img_bot - 10
                # If entirely off top edge, pull down
                elif img_bot <= 0:
                    clamp_dy = -img_top + 10
                if clamp_dx != 0 or clamp_dy != 0:
                    layer.Translate(clamp_dx, clamp_dy)
                    self.log(f"[CLAMP] Element was off-canvas, corrected by ({clamp_dx}, {clamp_dy}).")
            except:
                pass

            self._safe_set_blend_opacity(layer, blend_mode, opacity)

            # Remove background if requested
            if remove_bg:
                self._apply_select_subject_mask(layer)

            # Apply rotation around layer center (must be done after position+size)
            if rotation:
                try:
                    layer.Rotate(float(rotation), 1)  # 1 = psAnchorMiddle
                except Exception as e:
                    self.log(f"[WARN] Could not rotate element: {e}")

            idx = self._safe_get_index(layer)
            bounds = self._get_bounds(layer)
            bg_note = " (background removed)" if remove_bg else ""
            rot_note = f", rotation={rotation}°" if rotation else ""
            return (f"Element image placed at ({x},{y}), size {width}x{height}"
                    f"{bg_note}{rot_note}. Index: {idx}. Bounds: {bounds}")
        except Exception as e:
            self.log(f"[ERROR] Failed to add element: {e}")
            self._close_all_except_ours()
            self._ensure_active()
            return f"Error adding element image: {e}"

    def _apply_select_subject_mask(self, layer):
        """Apply Select Subject + Layer Mask to the given layer."""
        try:
            self.psd.ActiveLayer = layer
            js = (
                'var selDesc = new ActionDescriptor();\n'
                'selDesc.putBoolean(stringIDToTypeID("sampleAllLayers"), false);\n'
                'try {\n'
                '  executeAction(stringIDToTypeID("autoCutout"), selDesc, DialogModes.NO);\n'
                '} catch(e) {\n'
                '  try {\n'
                '    executeAction(stringIDToTypeID("selectSubject"), selDesc, DialogModes.NO);\n'
                '  } catch(e2) {}\n'
                '}\n'
                'var maskDesc = new ActionDescriptor();\n'
                'maskDesc.putClass(charIDToTypeID("Nw  "), charIDToTypeID("Chnl"));\n'
                'var ref = new ActionReference();\n'
                'ref.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Msk "));\n'
                'maskDesc.putReference(charIDToTypeID("At  "), ref);\n'
                'maskDesc.putEnumerated(charIDToTypeID("Usng"), charIDToTypeID("UsrM"), charIDToTypeID("RvlS"));\n'
                'executeAction(charIDToTypeID("Mk  "), maskDesc, DialogModes.NO);\n'
            )
            self.app.DoJavaScript(js)
        except Exception as e:
            self.log(f"[WARN] Select Subject failed: {e}")

    # ── Layer: Generative Fill (AI Image Generation) ─────────────────

    def generate_fill(self, prompt, x, y, width, height):
        """Use Photoshop's AI Generative Fill to generate content in a selected area."""
        try:
            self._ensure_active()

            # Escape prompt for JS string
            safe_prompt = (prompt.replace("\\", "\\\\")
                           .replace("'", "\\'")
                           .replace('"', '\\"')
                           .replace('\n', ' '))

            x2, y2 = x + width, y + height

            # Step 1: Create selection
            select_js = (
                f'var doc = app.activeDocument;\n'
                f'doc.selection.select([[{x},{y}],[{x2},{y}],[{x2},{y2}],[{x},{y2}]]);\n'
            )
            self.app.DoJavaScript(select_js)
            time.sleep(0.3)

            # Step 2: Run Generative Fill with correct PS action descriptors
            # Tries multiple known action IDs across PS versions
            gen_js = (
                'var success = false;\n'
                'var lastErr = "";\n'
                '\n'
                '// Method 1: PS 2024+ (v25) — recorded action format\n'
                'if (!success) {\n'
                '  try {\n'
                '    var d1 = new ActionDescriptor();\n'
                f'    d1.putString(stringIDToTypeID("GFPrompt"), "{safe_prompt}");\n'
                '    d1.putInteger(stringIDToTypeID("GFSeed"), -1);\n'
                '    d1.putInteger(stringIDToTypeID("GFNumVariations"), 1);\n'
                '    d1.putBoolean(stringIDToTypeID("GFPreserveLayers"), false);\n'
                '    executeAction(stringIDToTypeID("generativeFill"), d1, DialogModes.NO);\n'
                '    success = true;\n'
                '  } catch(e) { lastErr = e.message; }\n'
                '}\n'
                '\n'
                '// Method 2: PS 2025 / alternate action ID\n'
                'if (!success) {\n'
                '  try {\n'
                '    var d2 = new ActionDescriptor();\n'
                f'    d2.putString(stringIDToTypeID("GFPrompt"), "{safe_prompt}");\n'
                '    d2.putInteger(stringIDToTypeID("GFSeed"), -1);\n'
                '    d2.putInteger(stringIDToTypeID("GFNumVariations"), 1);\n'
                '    executeAction(stringIDToTypeID("syntheticFillGenerate"), d2, DialogModes.NO);\n'
                '    success = true;\n'
                '  } catch(e) { lastErr = e.message; }\n'
                '}\n'
                '\n'
                '// Method 3: Beta / early access versions\n'
                'if (!success) {\n'
                '  try {\n'
                '    var d3 = new ActionDescriptor();\n'
                f'    d3.putString(stringIDToTypeID("prompt"), "{safe_prompt}");\n'
                '    executeAction(stringIDToTypeID("neuralGalleryGenFill"), d3, DialogModes.NO);\n'
                '    success = true;\n'
                '  } catch(e) { lastErr = e.message; }\n'
                '}\n'
                '\n'
                'if (!success) {\n'
                '  throw new Error("Generative Fill failed. Requires Photoshop 2024+ with active Firefly subscription. Error: " + lastErr);\n'
                '}\n'
            )
            self.app.DoJavaScript(gen_js)

            # Generative fill processes through Adobe cloud — give it time
            time.sleep(8)

            # Deselect
            try:
                self.psd.Selection.Deselect()
            except:
                pass

            return f"Generative fill applied at ({x},{y}), size {width}x{height}. Prompt: '{prompt}'"
        except Exception as e:
            return f"Error with generative fill: {e}"

    # ── Layer: Solid Color ───────────────────────────────────────────

    def add_solid_color_layer(self, hex_color, blend_mode=1, opacity=100):
        try:
            self._ensure_active()
            hex_color = self._normalize_hex(hex_color)
            layer = self.psd.ArtLayers.Add()
            try:
                layer.Name = f"Color Fill {hex_color}"
            except:
                pass
            solidColor = win32.Dispatch("Photoshop.SolidColor")
            solidColor.RGB.HexValue = hex_color
            self.psd.Selection.SelectAll()
            self.psd.Selection.Fill(solidColor)
            self.psd.Selection.Deselect()
            self._safe_set_blend_opacity(layer, blend_mode, opacity)
            idx = self._safe_get_index(layer)
            return f"Solid color layer added successfully at index {idx}."
        except Exception as e:
            self.log(f"[ERROR] Failed to add solid color layer: {e}")
            return f"Error adding solid color layer: {e}"

    # ── Layer: Gradient ──────────────────────────────────────────────

    def add_gradient_layer(self, hex_color1, hex_color2, angle=90,
                           opacity=100, blend_mode=1):
        try:
            self._ensure_active()
            layer = self.psd.ArtLayers.Add()
            try:
                layer.Name = "Gradient"
            except:
                pass
            self.psd.ActiveLayer = layer

            r1, g1, b1 = self._hex_to_rgb(hex_color1)
            r2, g2, b2 = self._hex_to_rgb(hex_color2)
            w, h = self._get_canvas_size()

            cx, cy = w / 2, h / 2
            length = max(w, h)
            rad = math.radians(angle)
            x1 = cx - (length / 2) * math.cos(rad)
            y1 = cy - (length / 2) * math.sin(rad)
            x2 = cx + (length / 2) * math.cos(rad)
            y2 = cy + (length / 2) * math.sin(rad)

            js = (
                'app.activeDocument.selection.selectAll();\n'
                'var desc = new ActionDescriptor();\n'
                'desc.putEnumerated(charIDToTypeID("Type"),charIDToTypeID("GrdT"),charIDToTypeID("Lnr "));\n'
                'desc.putBoolean(charIDToTypeID("Dthr"),true);\n'
                'var fp=new ActionDescriptor();\n'
                f'fp.putUnitDouble(charIDToTypeID("Hrzn"),charIDToTypeID("#Pxl"),{x1:.0f});\n'
                f'fp.putUnitDouble(charIDToTypeID("Vrtc"),charIDToTypeID("#Pxl"),{y1:.0f});\n'
                'desc.putObject(charIDToTypeID("From"),charIDToTypeID("Pnt "),fp);\n'
                'var tp=new ActionDescriptor();\n'
                f'tp.putUnitDouble(charIDToTypeID("Hrzn"),charIDToTypeID("#Pxl"),{x2:.0f});\n'
                f'tp.putUnitDouble(charIDToTypeID("Vrtc"),charIDToTypeID("#Pxl"),{y2:.0f});\n'
                'desc.putObject(charIDToTypeID("T   "),charIDToTypeID("Pnt "),tp);\n'
                'var gd=new ActionDescriptor();\n'
                'gd.putString(charIDToTypeID("Nm  "),"Custom");\n'
                'gd.putEnumerated(charIDToTypeID("GrdF"),charIDToTypeID("GrdF"),charIDToTypeID("CstS"));\n'
                'gd.putDouble(charIDToTypeID("Intr"),4096);\n'
                'var cs=new ActionList();\n'
                'var s1=new ActionDescriptor();var c1=new ActionDescriptor();\n'
                f'c1.putDouble(charIDToTypeID("Rd  "),{r1});c1.putDouble(charIDToTypeID("Grn "),{g1});c1.putDouble(charIDToTypeID("Bl  "),{b1});\n'
                's1.putObject(charIDToTypeID("Clr "),charIDToTypeID("RGBC"),c1);\n'
                's1.putEnumerated(charIDToTypeID("Type"),charIDToTypeID("Clry"),charIDToTypeID("UsrS"));\n'
                's1.putInteger(charIDToTypeID("Lctn"),0);s1.putInteger(charIDToTypeID("Mdpn"),50);\n'
                'cs.putObject(charIDToTypeID("Clrt"),s1);\n'
                'var s2=new ActionDescriptor();var c2=new ActionDescriptor();\n'
                f'c2.putDouble(charIDToTypeID("Rd  "),{r2});c2.putDouble(charIDToTypeID("Grn "),{g2});c2.putDouble(charIDToTypeID("Bl  "),{b2});\n'
                's2.putObject(charIDToTypeID("Clr "),charIDToTypeID("RGBC"),c2);\n'
                's2.putEnumerated(charIDToTypeID("Type"),charIDToTypeID("Clry"),charIDToTypeID("UsrS"));\n'
                's2.putInteger(charIDToTypeID("Lctn"),4096);s2.putInteger(charIDToTypeID("Mdpn"),50);\n'
                'cs.putObject(charIDToTypeID("Clrt"),s2);\n'
                'gd.putList(charIDToTypeID("Clrs"),cs);\n'
                'var ts=new ActionList();\n'
                'var t1=new ActionDescriptor();t1.putUnitDouble(charIDToTypeID("Opct"),charIDToTypeID("#Prc"),100);\n'
                't1.putInteger(charIDToTypeID("Lctn"),0);t1.putInteger(charIDToTypeID("Mdpn"),50);\n'
                'ts.putObject(charIDToTypeID("TrnS"),t1);\n'
                'var t2=new ActionDescriptor();t2.putUnitDouble(charIDToTypeID("Opct"),charIDToTypeID("#Prc"),100);\n'
                't2.putInteger(charIDToTypeID("Lctn"),4096);t2.putInteger(charIDToTypeID("Mdpn"),50);\n'
                'ts.putObject(charIDToTypeID("TrnS"),t2);\n'
                'gd.putList(charIDToTypeID("Trns"),ts);\n'
                'desc.putObject(charIDToTypeID("Grad"),charIDToTypeID("Grdn"),gd);\n'
                'executeAction(charIDToTypeID("Grdn"),desc,DialogModes.NO);\n'
                'app.activeDocument.selection.deselect();'
            )
            self.app.DoJavaScript(js)
            self._safe_set_blend_opacity(layer, blend_mode, opacity)
            idx = self._safe_get_index(layer)
            return f"Gradient layer added successfully at index {idx}."
        except Exception as e:
            self.log(f"[ERROR] Failed to add gradient layer: {e}")
            return f"Error adding gradient layer: {e}"

    # ── Layer: Shape (Rectangle / Ellipse) ───────────────────────────

    def add_shape(self, shape_type, x, y, width, height, hex_color,
                  corner_radius=0, opacity=100, rotation=0):
        """Create a vector shape layer (rectangle or ellipse)."""
        try:
            self._ensure_active()
            r, g, b = self._hex_to_rgb(hex_color)
            x2, y2 = x + width, y + height

            if shape_type == "ellipse":
                shape_js = (
                    f'shape.putUnitDouble(charIDToTypeID("Top "),charIDToTypeID("#Pxl"),{y});\n'
                    f'shape.putUnitDouble(charIDToTypeID("Left"),charIDToTypeID("#Pxl"),{x});\n'
                    f'shape.putUnitDouble(charIDToTypeID("Btom"),charIDToTypeID("#Pxl"),{y2});\n'
                    f'shape.putUnitDouble(charIDToTypeID("Rght"),charIDToTypeID("#Pxl"),{x2});\n'
                )
                shape_key = "ellipse"
            else:
                shape_js = (
                    f'shape.putUnitDouble(charIDToTypeID("Top "),charIDToTypeID("#Pxl"),{y});\n'
                    f'shape.putUnitDouble(charIDToTypeID("Left"),charIDToTypeID("#Pxl"),{x});\n'
                    f'shape.putUnitDouble(charIDToTypeID("Btom"),charIDToTypeID("#Pxl"),{y2});\n'
                    f'shape.putUnitDouble(charIDToTypeID("Rght"),charIDToTypeID("#Pxl"),{x2});\n'
                    f'shape.putUnitDouble(stringIDToTypeID("topLeft"),charIDToTypeID("#Pxl"),{corner_radius});\n'
                    f'shape.putUnitDouble(stringIDToTypeID("topRight"),charIDToTypeID("#Pxl"),{corner_radius});\n'
                    f'shape.putUnitDouble(stringIDToTypeID("bottomLeft"),charIDToTypeID("#Pxl"),{corner_radius});\n'
                    f'shape.putUnitDouble(stringIDToTypeID("bottomRight"),charIDToTypeID("#Pxl"),{corner_radius});\n'
                )
                shape_key = "rectangle"

            js = (
                'var desc=new ActionDescriptor();\n'
                'var ref=new ActionReference();\n'
                'ref.putClass(stringIDToTypeID("contentLayer"));\n'
                'desc.putReference(charIDToTypeID("null"),ref);\n'
                'var using=new ActionDescriptor();\n'
                'var type=new ActionDescriptor();\n'
                'var clr=new ActionDescriptor();\n'
                f'clr.putDouble(charIDToTypeID("Rd  "),{r});\n'
                f'clr.putDouble(charIDToTypeID("Grn "),{g});\n'
                f'clr.putDouble(charIDToTypeID("Bl  "),{b});\n'
                'type.putObject(charIDToTypeID("Clr "),charIDToTypeID("RGBC"),clr);\n'
                'using.putObject(charIDToTypeID("Type"),stringIDToTypeID("solidColorLayer"),type);\n'
                'var shape=new ActionDescriptor();\n'
                + shape_js
                + f'using.putObject(charIDToTypeID("Shp "),stringIDToTypeID("{shape_key}"),shape);\n'
                'desc.putObject(charIDToTypeID("Usng"),stringIDToTypeID("contentLayer"),using);\n'
                'executeAction(charIDToTypeID("Mk  "),desc,DialogModes.NO);\n'
            )
            self.app.DoJavaScript(js)

            layer = self.psd.ActiveLayer
            self._safe_set_blend_opacity(layer, 1, opacity)

            # Apply rotation AFTER the shape is fully drawn so we rotate around its center
            if rotation:
                try:
                    layer.Rotate(float(rotation), 1)  # 1 = psAnchorMiddle
                except Exception as e:
                    self.log(f"[WARN] Could not rotate shape: {e}")

            idx = self._safe_get_index(layer)
            bounds = self._get_bounds(layer)
            rot_note = f", rotation={rotation}°" if rotation else ""
            return f"Shape ({shape_type}) added successfully at index {idx}{rot_note}. Bounds: {bounds}"
        except Exception as e:
            self.log(f"[ERROR] Failed to add shape: {e}")
            return f"Error adding shape: {e}"

    # ── Layer: Change Shape Color ─────────────────────────────────────

    def change_shape_color(self, index, hex_color):
        """Change the fill colour of an existing solid-colour shape layer."""
        try:
            self._ensure_active()
            all_layers = self.get_all_layers()
            if not (0 <= index < len(all_layers)):
                return "Layer index out of bounds."
            layer = all_layers[index]
            self.psd.ActiveLayer = layer
            r, g, b = self._hex_to_rgb(hex_color)
            js = (
                'var desc = new ActionDescriptor();\n'
                'var ref = new ActionReference();\n'
                'ref.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));\n'
                'desc.putReference(charIDToTypeID("null"), ref);\n'
                'var layerDesc = new ActionDescriptor();\n'
                'var shapeDesc = new ActionDescriptor();\n'
                'var colorDesc = new ActionDescriptor();\n'
                f'colorDesc.putDouble(charIDToTypeID("Rd  "), {r});\n'
                f'colorDesc.putDouble(charIDToTypeID("Grn "), {g});\n'
                f'colorDesc.putDouble(charIDToTypeID("Bl  "), {b});\n'
                'shapeDesc.putObject(charIDToTypeID("Clr "), charIDToTypeID("RGBC"), colorDesc);\n'
                'layerDesc.putObject(stringIDToTypeID("solidColorLayer"), stringIDToTypeID("solidColorLayer"), shapeDesc);\n'
                'desc.putObject(charIDToTypeID("T   "), stringIDToTypeID("contentLayer"), layerDesc);\n'
                'executeAction(charIDToTypeID("setd"), desc, DialogModes.NO);\n'
            )
            self.app.DoJavaScript(js)
            return f"Shape layer {index} colour changed to {hex_color}."
        except Exception as e:
            self.log(f"[ERROR] Failed to change shape colour: {e}")
            return f"Error changing shape colour: {e}"

    # ── Layer: Text ──────────────────────────────────────────────────

    def add_text_layer(self, content, font_size, hex_color, x, y,
                       blend_mode=1, opacity=100, font_name=None, alignment="left",
                       rotation=0, letter_spacing=None):
        try:
            self._ensure_active()
            cw, ch = self._get_canvas_size()

            layer = self.psd.ArtLayers.Add()
            layer.Kind = 2  # psTextLayer
            layer.TextItem.contents = content
            layer.TextItem.Size = font_size

            if font_name:
                try:
                    layer.TextItem.Font = font_name
                except:
                    pass

            # Set text color
            try:
                textColor = win32.Dispatch("Photoshop.SolidColor")
                textColor.RGB.HexValue = self._normalize_hex(hex_color)
                layer.TextItem.Color = textColor
            except:
                pass

            # Set text alignment/justification (1=Left, 2=Center, 3=Right)
            align_map = {"left": 1, "center": 2, "right": 3}
            align_val = align_map.get(str(alignment).lower(), 1)
            try:
                layer.TextItem.Justification = align_val
            except:
                pass

            # Letter spacing (tracking) — used by condensed/headline fonts
            if letter_spacing is not None:
                try:
                    layer.TextItem.Tracking = float(letter_spacing)
                except Exception:
                    pass

            layer.TextItem.Position = [x, y]
            self._safe_set_blend_opacity(layer, blend_mode, opacity)

            # Rotate AFTER positioning so the rotation pivots around the text center
            if rotation:
                try:
                    layer.Rotate(float(rotation), 1)  # 1 = psAnchorMiddle
                except Exception as e:
                    self.log(f"[WARN] Could not rotate text: {e}")

            idx = self._safe_get_index(layer)
            bounds = self._get_bounds(layer)
            rot_note = f", rotation={rotation}°" if rotation else ""
            return f"Text layer added successfully at index {idx}{rot_note}. Bounds: {bounds}"
        except Exception as e:
            self.log(f"[ERROR] Failed to add text layer: {e}")
            return f"Error adding text layer: {e}"

    # ── Pattern: Pill CTA (shape + centered text in one call) ────────

    def add_pill_cta(self, text, x, y, width, height, pill_color,
                     text_color="#ffffff", font_size=None, font_name=None,
                     corner_radius=None):
        """Create a CTA pill (rounded rectangle) and centered text on top.
        This is the FIGO-style 'corner-anchored CTA pill' pattern — the
        single most important hero element in modern social posts.
        Returns a combined status message.
        """
        try:
            self._ensure_active()

            # Auto corner radius: fully rounded by default (Apple-style pill)
            if corner_radius is None:
                corner_radius = height // 2

            # Create the pill shape first (sits below the text)
            pill_result = self.add_shape(
                "rectangle", x, y, width, height, pill_color,
                corner_radius=corner_radius, opacity=100,
            )

            # Auto font size: ~38% of pill height when not specified
            if font_size is None:
                font_size = max(18, int(height * 0.38))

            # Center text horizontally in pill, baseline ~70% down from top
            cx = x + width // 2
            baseline_y = y + int(height * 0.5 + font_size * 0.32)

            text_result = self.add_text_layer(
                text, font_size, text_color, cx, baseline_y,
                blend_mode=1, opacity=100, font_name=font_name,
                alignment="center",
            )

            return (
                f"PILL CTA created at ({x},{y}) size {width}x{height}, "
                f"radius={corner_radius}, color={pill_color}. "
                f"Pill: {pill_result} | Text: {text_result}"
            )
        except Exception as e:
            self.log(f"[ERROR] Failed to add pill CTA: {e}")
            return f"Error adding pill CTA: {e}"

    # ── Layer: Move ──────────────────────────────────────────────────

    def move_layer(self, index, delta_x, delta_y):
        try:
            self._ensure_active()
            all_layers = self.get_all_layers()
            if 0 <= index < len(all_layers):
                layer = all_layers[index]
                layer.Translate(delta_x, delta_y)
                bounds = self._get_bounds(layer)
                return f"Layer {index} moved by ({delta_x},{delta_y}). New bounds: {bounds}"
            return "Layer index out of bounds."
        except Exception as e:
            return f"Error moving layer: {e}"

    # ── Layer: Rotate ────────────────────────────────────────────────

    def rotate_layer(self, index, angle):
        """Rotate a layer by degrees around its center."""
        try:
            self._ensure_active()
            all_layers = self.get_all_layers()
            if 0 <= index < len(all_layers):
                layer = all_layers[index]
                layer.Rotate(angle, 1)  # 1 = psAnchorMiddle
                bounds = self._get_bounds(layer)
                return f"Layer {index} rotated by {angle}°. Bounds: {bounds}"
            return "Layer index out of bounds."
        except Exception as e:
            return f"Error rotating layer: {e}"

    # ── Layer: Scale ─────────────────────────────────────────────────

    def scale_layer(self, index, scale_percent):
        """Scale a layer uniformly by percentage (100 = no change, 50 = half, 200 = double)."""
        try:
            self._ensure_active()
            all_layers = self.get_all_layers()
            if 0 <= index < len(all_layers):
                layer = all_layers[index]
                layer.Resize(scale_percent, scale_percent, 1)  # 1 = psAnchorMiddle
                bounds = self._get_bounds(layer)
                return f"Layer {index} scaled to {scale_percent}%. Bounds: {bounds}"
            return "Layer index out of bounds."
        except Exception as e:
            return f"Error scaling layer: {e}"

    # ── Layer: Stroke (Layer Style) ──────────────────────────────────

    def add_stroke(self, index, thickness, hex_color):
        """Add a stroke layer style to the specified layer."""
        try:
            self._ensure_active()
            all_layers = self.get_all_layers()
            if 0 <= index < len(all_layers):
                layer = all_layers[index]
                self.psd.ActiveLayer = layer

                r, g, b = self._hex_to_rgb(hex_color)
                js = (
                    'var desc=new ActionDescriptor();\n'
                    'var ref=new ActionReference();\n'
                    'ref.putProperty(charIDToTypeID("Prpr"),charIDToTypeID("Lefx"));\n'
                    'ref.putEnumerated(charIDToTypeID("Lyr "),charIDToTypeID("Ordn"),charIDToTypeID("Trgt"));\n'
                    'desc.putReference(charIDToTypeID("null"),ref);\n'
                    'var fx=new ActionDescriptor();\n'
                    'fx.putUnitDouble(charIDToTypeID("Scl "),charIDToTypeID("#Prc"),100);\n'
                    'var st=new ActionDescriptor();\n'
                    'st.putBoolean(charIDToTypeID("enab"),true);\n'
                    'st.putEnumerated(charIDToTypeID("Styl"),charIDToTypeID("FStl"),charIDToTypeID("OutF"));\n'
                    'st.putEnumerated(charIDToTypeID("PntT"),charIDToTypeID("FrFl"),charIDToTypeID("SClr"));\n'
                    f'st.putUnitDouble(charIDToTypeID("Sz  "),charIDToTypeID("#Pxl"),{thickness});\n'
                    'st.putUnitDouble(charIDToTypeID("Opct"),charIDToTypeID("#Prc"),100);\n'
                    'var clr=new ActionDescriptor();\n'
                    f'clr.putDouble(charIDToTypeID("Rd  "),{r});\n'
                    f'clr.putDouble(charIDToTypeID("Grn "),{g});\n'
                    f'clr.putDouble(charIDToTypeID("Bl  "),{b});\n'
                    'st.putObject(charIDToTypeID("Clr "),charIDToTypeID("RGBC"),clr);\n'
                    'fx.putObject(charIDToTypeID("FrFX"),charIDToTypeID("FrFX"),st);\n'
                    'desc.putObject(charIDToTypeID("T   "),charIDToTypeID("Lefx"),fx);\n'
                    'executeAction(charIDToTypeID("setd"),desc,DialogModes.NO);\n'
                )
                self.app.DoJavaScript(js)
                return f"Stroke ({thickness}px, {hex_color}) added to layer {index}."
            return "Layer index out of bounds."
        except Exception as e:
            return f"Error adding stroke: {e}"

    # ── Layer: Reorder ───────────────────────────────────────────────

    def reorder_layer(self, index, new_index):
        """Move a layer from one position to another in the layer stack."""
        try:
            self._ensure_active()
            all_layers = self.get_all_layers()
            if not (0 <= index < len(all_layers)):
                return "Source layer index out of bounds."
            if not (0 <= new_index < len(all_layers)):
                return "Target layer index out of bounds."
            if index == new_index:
                return "Layer is already at the specified position."

            src = all_layers[index]
            tgt = all_layers[new_index]

            if new_index < index:
                src.Move(tgt, 1)  # PlaceBefore (above target)
            else:
                src.Move(tgt, 2)  # PlaceAfter (below target)

            return f"Layer moved from index {index} to {new_index}."
        except Exception as e:
            return f"Error reordering layer: {e}"

    # ── Layer: Select Subject + Mask ─────────────────────────────────

    def select_subject_and_mask(self, index):
        """Use Photoshop AI 'Select Subject' on a layer and apply a layer mask from the selection."""
        try:
            self._ensure_active()
            all_layers = self.get_all_layers()
            if not (0 <= index < len(all_layers)):
                return "Layer index out of bounds."

            layer = all_layers[index]
            self._apply_select_subject_mask(layer)
            return f"Subject selected and mask applied to layer {index}."
        except Exception as e:
            return f"Error selecting subject/applying mask: {e}"

    # ── Layer: Properties ────────────────────────────────────────────

    def set_layer_properties(self, index, text=None, font_size=None,
                             opacity=None, blend_mode=None, font_name=None,
                             hex_color=None):
        try:
            self._ensure_active()
            all_layers = self.get_all_layers()
            if 0 <= index < len(all_layers):
                layer = all_layers[index]
                if text is not None and layer.Kind == 2:
                    layer.TextItem.contents = text
                if font_size is not None and layer.Kind == 2:
                    layer.TextItem.Size = font_size
                if font_name is not None and layer.Kind == 2:
                    try:
                        layer.TextItem.Font = font_name
                    except:
                        pass
                if hex_color is not None and layer.Kind == 2:
                    try:
                        c = self._normalize_hex(hex_color)
                        tc = win32.Dispatch("Photoshop.SolidColor")
                        tc.RGB.HexValue = c
                        layer.TextItem.Color = tc
                    except:
                        pass
                if opacity is not None:
                    try:
                        layer.Opacity = opacity
                    except:
                        pass
                if blend_mode is not None:
                    try:
                        layer.BlendMode = blend_mode
                    except:
                        pass

                # Auto-fix text position if it went off canvas
                if layer.Kind == 2:
                    self._auto_fix_bounds(layer)

                bounds = self._get_bounds(layer)
                return f"Layer {index} properties updated. Bounds: {bounds}"
            return "Layer index out of bounds."
        except Exception as e:
            return f"Error updating layer properties: {e}"

    # ── Context ──────────────────────────────────────────────────────

    # Blend mode int → name map for readable context
    _BLEND_NAMES = {
        1:"Normal",2:"Dissolve",3:"Darken",4:"Multiply",5:"ColorBurn",
        6:"LinearBurn",7:"Lighten",8:"Screen",9:"ColorDodge",10:"LinearDodge",
        11:"Overlay",12:"SoftLight",13:"HardLight",14:"VividLight",
        15:"LinearLight",16:"PinLight",17:"HardMix",18:"Difference",
        19:"Exclusion",20:"Hue",21:"Saturation",22:"Color",23:"Luminosity",
    }
    _KIND_NAMES = {
        1:"normal",2:"text",3:"solid",4:"pattern",5:"gradient",
        6:"smart_object",7:"video",8:"group",9:"3d",
    }
    _JUST_NAMES = {1:"left",2:"center",3:"right",4:"full"}

    def get_layer_context(self):
        """Return a rich layer context dict with every attribute PS exposes via COM."""
        self._ensure_active()
        fonts_seen = set()
        cw, ch = self._get_canvas_size()
        context = {"resolution": f"{cw}x{ch}", "canvas_w": cw, "canvas_h": ch,
                   "layers": [], "fonts_used": []}

        for i, lyr in enumerate(self.get_all_layers()):
            try:
                info = {"index": i}
                # Basic
                try: info["name"] = lyr.Name
                except: info["name"] = f"layer_{i}"
                try: info["visible"] = bool(lyr.Visible)
                except: pass
                try: info["opacity"] = round(float(lyr.Opacity), 1)
                except: info["opacity"] = 100
                try:
                    bm = int(lyr.BlendMode)
                    info["blend_mode"] = self._BLEND_NAMES.get(bm, f"mode_{bm}")
                except: info["blend_mode"] = "Normal"

                # Kind / type
                lkind = 0
                try: lkind = int(lyr.Kind)
                except: pass
                info["kind"] = self._KIND_NAMES.get(lkind, "group" if lkind == 0 else f"kind_{lkind}")

                # Bounds + center
                try:
                    b = lyr.Bounds
                    l, t, r, bt = int(b[0]), int(b[1]), int(b[2]), int(b[3])
                    w, h = r - l, bt - t
                    info["bounds"] = {
                        "left": l, "top": t, "right": r, "bottom": bt,
                        "width": w, "height": h,
                        "center_x": l + w // 2, "center_y": t + h // 2,
                    }
                except: pass

                # Text layer extras
                if lkind == 2:
                    try: info["text"] = lyr.TextItem.contents
                    except: info["text"] = ""
                    try:
                        f = lyr.TextItem.Font
                        info["font"] = f
                        fonts_seen.add(f)
                    except: pass
                    try: info["font_size"] = round(float(lyr.TextItem.Size), 1)
                    except: pass
                    try:
                        pos = lyr.TextItem.Position
                        info["text_position"] = [round(float(pos[0]), 1), round(float(pos[1]), 1)]
                    except: pass
                    try:
                        c = lyr.TextItem.Color.RGB
                        hr = int(round(float(c.Red)))
                        hg = int(round(float(c.Green)))
                        hb = int(round(float(c.Blue)))
                        info["color_hex"] = f"#{hr:02x}{hg:02x}{hb:02x}"
                    except: pass
                    try:
                        j = int(lyr.TextItem.Justification)
                        info["alignment"] = self._JUST_NAMES.get(j, "left")
                    except: info["alignment"] = "left"
                    try: info["leading"] = round(float(lyr.TextItem.Leading), 1)
                    except: pass
                    try: info["tracking"] = round(float(lyr.TextItem.Tracking), 1)
                    except: pass

                context["layers"].append(info)
            except:
                pass

        context["fonts_used"] = sorted(fonts_seen)
        return context

    # ── Export ────────────────────────────────────────────────────────

    def export_preview(self, output_path):
        try:
            if not self.psd:
                return False
            self._ensure_active()
            options = win32.Dispatch("Photoshop.ExportOptionsSaveForWeb")
            options.Format = 13
            options.PNG8 = False
            self.psd.Export(output_path, 2, options)
            return True
        except Exception as e:
            self.log(f"[ERROR] Export failed: {e}")
            return False
