from desain.local_llm.capabilities import profile_model


def test_tiny_model_prefers_json_actions():
    profile = profile_model("qwen2.5-0.5b-instruct")
    assert profile.size == "tiny"
    assert profile.tool_mode == "json_actions"
    assert profile.use_few_shot is True
    assert profile.temperature <= 0.3


def test_strong_model_prefers_native_tools():
    profile = profile_model("qwen2.5-14b-instruct")
    assert profile.size in {"medium", "large"}
    assert profile.tool_mode == "native"
    assert profile.self_check is True


def test_force_tool_mode():
    profile = profile_model("mystery-model", force_tool_mode="text_only")
    assert profile.tool_mode == "text_only"
