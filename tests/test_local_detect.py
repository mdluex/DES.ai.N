from desain.local_llm.detect import DetectedEndpoint, pick_best_endpoint, probe_endpoint


def test_probe_endpoint_unreachable():
    assert probe_endpoint("http://127.0.0.1:59999/v1", timeout_s=0.2) is None


def test_pick_best_prefers_lmstudio():
    endpoints = [
        DetectedEndpoint("ollama", "http://127.0.0.1:11434/v1", models=["llama3"]),
        DetectedEndpoint("lmstudio", "http://127.0.0.1:1234/v1", models=["qwen"]),
    ]
    best = pick_best_endpoint(endpoints)
    assert best is not None
    assert best.provider == "lmstudio"


def test_pick_best_by_preferred_model():
    endpoints = [
        DetectedEndpoint("lmstudio", "http://127.0.0.1:1234/v1", models=["other"]),
        DetectedEndpoint("ollama", "http://127.0.0.1:11434/v1", models=["llava-7b"]),
    ]
    best = pick_best_endpoint(endpoints, preferred_model="llava")
    assert best is not None
    assert best.provider == "ollama"
