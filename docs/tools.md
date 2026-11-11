# Tools

The desktop agent and the optional MCP server share the same Photoshop capability
set. Mutating operations create a history checkpoint when
`DESAIN_HISTORY_CHECKPOINT=true`.

| Tool | Description |
|---|---|
| `open_template` | Open a `.psd` / `.psb` from the templates library |
| `create_canvas` | New document |
| `get_layer_context` | Layer map, fonts, canvas size |
| `add_text_layer` | Create text (y = baseline) |
| `set_layer_properties` | Edit text / font / color / opacity |
| `move_layer` / `rotate_layer` / `scale_layer` / `reorder_layer` | Transform / stack |
| `add_solid_color_layer` / `add_gradient_layer` / `add_shape` | Fills and vectors |
| `change_shape_color` / `add_stroke` | Recolor / outline |
| `add_image_layer` / `add_element_layer` | Imagery (Unsplash or local path) |
| `add_pill_cta` | Rounded CTA pill + text |
| `select_subject_and_mask` | Select Subject + mask |
| `generate_fill` | Generative Fill (Photoshop 2024+) |
| `save_document` / `close_document` | Export / close |
| `finalize_design` | QA + save + complete (desktop agent) |
| `history_checkpoint` / `history_undo` | Explicit history control (MCP) |

Custom tools can be added under `plugins/` for the MCP server.
