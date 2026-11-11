# MCP tools

All mutating tools create a Photoshop history checkpoint when
`DESAIN_HISTORY_CHECKPOINT=true` (default).

| Tool | Mutating | Description |
|---|---|---|
| `photoshop_status` | no | Bridge + Photoshop connection status |
| `list_templates` | no | List `.psd` / `.psb` templates |
| `open_template` | yes | Open template and return layer context |
| `create_canvas` | yes | New document |
| `get_layer_context` | no | Layer map + fonts + canvas size |
| `add_text_layer` | yes | Create text (y = baseline) |
| `set_layer_properties` | yes | Edit text/font/color/opacity |
| `move_layer` | yes | Translate by delta |
| `rotate_layer` | yes | Rotate around center |
| `scale_layer` | yes | Uniform scale % |
| `reorder_layer` | yes | Restack |
| `add_solid_color_layer` | yes | Solid fill |
| `add_gradient_layer` | yes | Linear gradient |
| `add_shape` | yes | Rectangle / ellipse / circle |
| `change_shape_color` | yes | Recolor shape |
| `add_stroke` | yes | Outline style |
| `add_image_layer` | yes | Full-canvas image (Unsplash or path) |
| `add_element_layer` | yes | Positioned image element |
| `add_pill_cta` | yes | Rounded CTA pill + text |
| `select_subject_and_mask` | yes | Select Subject + mask |
| `generate_fill` | yes | Generative Fill (PS 2024+) |
| `save_document` | no* | Export PNG (+ optional PSD/PSB) |
| `close_document` | yes | Close without saving |
| `history_checkpoint` | no | Explicit snapshot |
| `history_undo` | no | Undo N steps |
| `example_echo` | no | Sample plugin tool |

\*Save writes files but does not create a history checkpoint by default.

## Escape hatches

Raw `execute_jsx` / `execute_batchplay` are available on the service layer when
`DESAIN_ALLOW_DESTRUCTIVE=true`. They are intentionally not registered as default
MCP tools in the public surface to reduce accidental damage; enable and wire them
in a private fork or plugin if needed.

## Custom plugins

Drop a Python file in `plugins/`:

```python
async def my_tool(name: str) -> dict:
    return {"hello": name}

PLUGIN = {
    "name": "mine",
    "tools": [{
        "name": "my_tool",
        "description": "Say hello",
        "handler": my_tool,
    }],
}
```

Restart the MCP server to load new plugins.
