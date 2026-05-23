"""
Photoshop Template Inspector — Opens a .psd or .psb via Photoshop COM and
extracts every layer's typography, color, and geometry into a structured
JSON report.

Both .psd (standard Photoshop document) and .psb ("Photoshop Big" — used
for documents larger than 30,000 px or 2 GB) are supported transparently.

Usage:
    python -m utils.inspect_psd "templates\\FIGO Ride hailing app - Social media post.psd"
    python -m utils.inspect_psd "templates\\Mutqan Ramadan Banner.psb"
    python -m utils.inspect_psd                  # defaults to FIGO template

Output:
    Prints a human-readable summary to stdout AND writes a JSON file next to
    the source PSD/PSB with the same basename + ".inspect.json".
"""
import os
import sys
import json
import time

# Force UTF-8 stdout so Arabic text and Unicode glyphs print without crashing.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.photoshop_client import PhotoshopClient
from utils.templates import is_photoshop_template


def _safe(getter, default=None):
    try:
        return getter()
    except Exception:
        return default


def _color_to_hex(color):
    try:
        rgb = color.RGB
        r = int(round(float(rgb.Red)))
        g = int(round(float(rgb.Green)))
        b = int(round(float(rgb.Blue)))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return None


def inspect_psd(path: str) -> dict:
    client = PhotoshopClient(log_callback=lambda m: print(m))
    client.connect()

    print(f"[INFO] Opening: {path}")
    client.open_document(path)
    time.sleep(0.5)
    doc = client.psd

    report = {
        "file": os.path.basename(path),
        "canvas_w": int(doc.Width),
        "canvas_h": int(doc.Height),
        "resolution_dpi": _safe(lambda: int(doc.Resolution), 72),
        "color_mode": _safe(lambda: int(doc.Mode), None),
        "layer_count": 0,
        "text_layers": [],
        "shape_layers": [],
        "image_layers": [],
        "groups": [],
        "fonts_used": [],
        "color_palette": [],
        "raw_layers": [],
    }

    fonts = set()
    colors = []

    def walk(layers, depth=0, parent="(root)"):
        for layer in layers:
            try:
                name = _safe(lambda: layer.Name, "<unnamed>")
                kind = _safe(lambda: int(layer.Kind), 0)
                visible = _safe(lambda: bool(layer.Visible), True)
                opacity = _safe(lambda: round(float(layer.Opacity), 1), 100)
                blend = _safe(lambda: int(layer.BlendMode), 1)

                # Group?
                try:
                    sub = layer.Layers
                    if sub and sub.Count > 0:
                        report["groups"].append({"name": name, "parent": parent, "children": sub.Count})
                        walk(sub, depth + 1, name)
                        continue
                except Exception:
                    pass

                bounds = _safe(lambda: layer.Bounds)
                left = top = right = bot = None
                if bounds:
                    try:
                        left, top, right, bot = int(bounds[0]), int(bounds[1]), int(bounds[2]), int(bounds[3])
                    except Exception:
                        pass

                base = {
                    "name": name,
                    "kind": kind,
                    "parent": parent,
                    "visible": visible,
                    "opacity": opacity,
                    "blend_mode": blend,
                    "bounds": {"left": left, "top": top, "right": right, "bottom": bot}
                        if left is not None else None,
                }

                if kind == 2:  # Text layer
                    ti = layer.TextItem
                    content = _safe(lambda: ti.contents, "")
                    font = _safe(lambda: ti.Font, "")
                    size = _safe(lambda: round(float(ti.Size), 1), None)
                    color_hex = _color_to_hex(_safe(lambda: ti.Color))
                    just = _safe(lambda: int(ti.Justification), 1)
                    leading = _safe(lambda: round(float(ti.Leading), 1), None)
                    tracking = _safe(lambda: round(float(ti.Tracking), 1), None)
                    text_pos = _safe(lambda: [round(float(ti.Position[0]), 1),
                                              round(float(ti.Position[1]), 1)], None)

                    if font:
                        fonts.add(font)
                    if color_hex:
                        colors.append(color_hex)

                    text_info = {
                        **base,
                        "content": content,
                        "font": font,
                        "font_size_pt": size,
                        "color": color_hex,
                        "alignment": {1: "left", 2: "center", 3: "right", 4: "full"}.get(just, str(just)),
                        "leading": leading,
                        "tracking": tracking,
                        "text_position": text_pos,
                    }
                    report["text_layers"].append(text_info)
                elif kind in (3, 4, 5):  # Solid / Pattern / Gradient fill
                    report["shape_layers"].append(base)
                else:
                    report["image_layers"].append(base)

                report["raw_layers"].append(base)
            except Exception as e:
                print(f"[WARN] could not introspect layer: {e}")

    walk(doc.Layers)
    report["layer_count"] = len(report["raw_layers"])
    report["fonts_used"] = sorted(fonts)

    # Color palette: top occurrences from text colors first
    from collections import Counter
    cnt = Counter(colors)
    report["color_palette"] = [c for c, _ in cnt.most_common(20)]

    # Save JSON next to PSD
    json_path = os.path.splitext(path)[0] + ".inspect.json"
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[OK] Wrote inspection report → {json_path}")
    except Exception as e:
        print(f"[WARN] Could not write JSON: {e}")

    # Close the doc (don't save)
    try:
        doc.Close(2)
    except Exception:
        pass

    # Print summary
    print("\n" + "=" * 64)
    print(f"  PSD INSPECTION SUMMARY  -  {report['file']}")
    print("=" * 64)
    print(f"Canvas        : {report['canvas_w']} x {report['canvas_h']}px  "
          f"@ {report['resolution_dpi']} dpi")
    print(f"Total layers  : {report['layer_count']}")
    print(f"Text layers   : {len(report['text_layers'])}")
    print(f"Shape layers  : {len(report['shape_layers'])}")
    print(f"Image layers  : {len(report['image_layers'])}")
    print(f"Groups        : {len(report['groups'])}")
    print(f"\nFonts used:")
    for f in report["fonts_used"]:
        print(f"   - {f}")
    print(f"\nColor palette (from text):")
    for c in report["color_palette"]:
        print(f"   - {c}")
    print(f"\nText content:")
    for t in report["text_layers"]:
        b = t.get("bounds") or {}
        print(
            f"   [{t['name']}] "
            f"\"{(t.get('content') or '').strip()[:60]}\""
            f"\n        font={t.get('font')}  size={t.get('font_size_pt')}pt  "
            f"color={t.get('color')}  align={t.get('alignment')}"
            f"\n        bounds=({b.get('left')},{b.get('top')})-({b.get('right')},{b.get('bottom')})"
        )
    print("=" * 64)
    return report


def main():
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates",
            "FIGO Ride hailing app - Social media post.psd"
        )

    if not os.path.isabs(target):
        target = os.path.abspath(target)

    if not os.path.exists(target):
        print(f"[ERROR] File not found: {target}")
        sys.exit(1)

    if not is_photoshop_template(target):
        print(f"[ERROR] Unsupported file type: {target}")
        print("       Only .psd and .psb files can be inspected.")
        sys.exit(2)

    inspect_psd(target)


if __name__ == "__main__":
    main()
