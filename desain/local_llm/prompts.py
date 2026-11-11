"""Model-aware prompt fragments for local design agents."""

from __future__ import annotations

from desain.local_llm.capabilities import ModelProfile
from desain.local_llm.json_tools import build_json_action_schema_prompt

FEW_SHOT_DESIGN_EXAMPLES = """
FEW-SHOT EXAMPLES (follow this style of tool use):

User: Create a dark 1080x1080 social post that says "NIGHT DRIVE"
Assistant plan:
1) create_canvas(width=1080, height=1080, filename="night_drive")
2) add_solid_color_layer(hex_color="#0a0a1a")
3) add_text_layer(content="NIGHT DRIVE", font_size=90, hex_color="#FFFFFF", x=540, y=520, alignment="center")
4) finalize_design(message="Dark cinematic social post ready", filename="night_drive")

User: Open the figo template and change the headline to "Ride the Future"
Assistant plan:
1) open_template(filename="figo")
2) Read LAYER MAP, find the headline text index
3) set_layer_properties(index=<headline_index>, text="Ride the Future")
4) finalize_design(message="Updated headline", filename="figo_ride")
""".strip()


def tool_summaries_from_openai_tools(tools: list[dict]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in tools:
        fn = item.get("function") if isinstance(item, dict) else None
        if not isinstance(fn, dict):
            continue
        name = str(fn.get("name") or "")
        desc = str(fn.get("description") or name)
        if name:
            out.append({"name": name, "description": desc[:180]})
    return out


def augment_system_prompt(
    base_prompt: str,
    profile: ModelProfile,
    *,
    tools: list[dict] | None = None,
    json_mode: bool = False,
) -> str:
    parts = [base_prompt.rstrip()]

    parts.append(
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  LOCAL MODEL OPERATING RULES\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Model profile: size={profile.size}, tool_mode={profile.tool_mode}.\n"
        "Work in small steps. After each tool result, re-read bounds before placing the next element.\n"
        "Prefer editing existing template layers over inventing new ones when a template is open.\n"
    )

    if profile.step_planning:
        parts.append(
            "Before the first edit, silently plan 3-6 steps (canvas/template → background → "
            "hero/text → CTA → finalize).\n"
        )

    if profile.self_check:
        parts.append(
            "SELF-CHECK: before finalize_design, confirm every text layer is on-canvas and that "
            "you used layer indexes from the latest LAYER MAP.\n"
        )

    if profile.use_few_shot:
        parts.append("\n" + FEW_SHOT_DESIGN_EXAMPLES + "\n")

    if json_mode and tools is not None:
        summaries = tool_summaries_from_openai_tools(tools)
        parts.append("\n" + build_json_action_schema_prompt(summaries) + "\n")

    return "\n".join(parts)


def trim_messages(messages: list, max_messages: int) -> list:
    """Keep system + recent turns to fit small-model context windows."""
    if max_messages <= 0 or len(messages) <= max_messages:
        return messages
    system = [m for m in messages if isinstance(m, dict) and m.get("role") == "system"]
    rest = [m for m in messages if not (isinstance(m, dict) and m.get("role") == "system")]
    keep = max(1, max_messages - len(system))
    return system + rest[-keep:]
