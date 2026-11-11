from desain.local_llm.capabilities import profile_model
from desain.local_llm.prompts import augment_system_prompt, trim_messages


def test_trim_keeps_system_and_tail():
    messages = [{"role": "system", "content": "sys"}] + [
        {"role": "user", "content": f"m{i}"} for i in range(20)
    ]
    trimmed = trim_messages(messages, 5)
    assert trimmed[0]["role"] == "system"
    assert len(trimmed) <= 5
    assert trimmed[-1]["content"] == "m19"


def test_augment_adds_json_schema_for_small_models():
    profile = profile_model("phi-2")
    tools = [
        {
            "type": "function",
            "function": {"name": "create_canvas", "description": "Make a canvas"},
        }
    ]
    text = augment_system_prompt("BASE", profile, tools=tools, json_mode=True)
    assert "BASE" in text
    assert "create_canvas" in text
    assert "JSON object" in text
