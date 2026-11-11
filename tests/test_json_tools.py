import json

from desain.local_llm.json_tools import (
    extract_json_payload,
    parse_tool_calls_from_text,
    repair_json_text,
    validate_tool_call,
)


def test_extract_from_markdown_fence():
    text = """Sure!
```json
{"actions":[{"tool":"create_canvas","arguments":{"width":1080,"height":1080,"filename":"ad"}}],"done":false}
```
"""
    payload = extract_json_payload(text)
    assert payload is not None
    data = json.loads(payload)
    assert data["actions"][0]["tool"] == "create_canvas"


def test_repair_trailing_comma_and_single_quotes():
    raw = "{'tool': 'add_text_layer', 'arguments': {'content': 'Hi',},}"
    repaired = repair_json_text(raw)
    data = json.loads(repaired)
    assert data["tool"] == "add_text_layer"
    assert data["arguments"]["content"] == "Hi"


def test_repair_python_literals_and_truncation():
    raw = '{"done": True, "actions": [{"tool": "close_document", "arguments": {}}]'
    repaired = repair_json_text(raw)
    data = json.loads(repaired)
    assert data["done"] is True
    assert data["actions"][0]["tool"] == "close_document"


def test_parse_action_plan():
    text = json.dumps(
        {
            "thinking": "Make a canvas",
            "actions": [
                {
                    "tool": "create_canvas",
                    "arguments": {"width": 1080, "height": 1080, "filename": "x"},
                }
            ],
            "message": "Starting",
            "done": False,
        }
    )
    calls, message, done = parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0].name == "create_canvas"
    assert message == "Starting"
    assert done is False


def test_parse_single_tool_shorthand_and_array():
    calls, _, _ = parse_tool_calls_from_text(
        '{"name":"move_layer","arguments":{"index":0,"delta_x":1,"delta_y":2}}'
    )
    assert calls[0].name == "move_layer"
    assert calls[0].arguments["delta_x"] == 1

    calls2, _, _ = parse_tool_calls_from_text(
        '[{"tool":"rotate_layer","args":{"index":1,"angle":15}}]'
    )
    assert calls2[0].name == "rotate_layer"
    assert calls2[0].arguments["angle"] == 15


def test_parse_repairs_fenced_broken_json():
    text = """```json
{"actions":[{"tool":"finalize_design","arguments":{"message":"Done","filename":"out",}}],"done":true,}
```"""
    calls, message, done = parse_tool_calls_from_text(text)
    assert calls[0].name == "finalize_design"
    assert done is True
    assert calls[0].source in {"json", "repaired"}


def test_validate_tool_call_required_keys():
    ok, err, _ = validate_tool_call("create_canvas", {"width": 1})
    assert ok is False
    assert "Missing" in (err or "")

    ok2, err2, cleaned = validate_tool_call(
        "create_canvas", {"width": 1080, "height": 1080, "filename": "ad"}
    )
    assert ok2 is True
    assert err2 is None
    assert cleaned["filename"] == "ad"


def test_validate_unknown_tool():
    ok, err, _ = validate_tool_call("launch_missiles", {})
    assert ok is False
    assert "Unknown" in (err or "")
