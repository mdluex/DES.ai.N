from desain.config import Settings
from desain.llm import resolve_llm_config


def test_default_provider_is_local_not_cloud():
    settings = Settings(llm_provider="local", llm_base_url="http://127.0.0.1:1234/v1")
    cfg = resolve_llm_config(settings)
    assert cfg.is_local is True
    assert "openai.com" not in cfg.base_url


def test_explicit_cloud_provider():
    settings = Settings(llm_provider="groq", llm_api_key="g", llm_base_url="http://ignored")
    cfg = resolve_llm_config(settings)
    assert cfg.is_local is False
    assert cfg.base_url.startswith("https://api.groq.com")


def test_lmstudio_provider_label():
    settings = Settings(llm_provider="lmstudio", llm_api_key="")
    cfg = resolve_llm_config(settings)
    assert cfg.provider == "lmstudio"
    assert cfg.is_local is True
