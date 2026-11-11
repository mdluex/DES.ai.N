from desain.config import Settings
from desain.llm import resolve_llm_config


def test_resolve_groq_provider():
    settings = Settings(llm_provider="groq", llm_api_key="g", llm_base_url="http://ignored")
    cfg = resolve_llm_config(settings)
    assert cfg.base_url.startswith("https://api.groq.com")


def test_resolve_openai_compatible_keeps_custom_base():
    settings = Settings(
        llm_provider="openai_compatible",
        llm_base_url="http://localhost:1234/v1",
        llm_api_key="x",
    )
    cfg = resolve_llm_config(settings)
    assert cfg.base_url == "http://localhost:1234/v1"
