"""Legacy config shim.

Prefer environment variables / ``.env`` via ``desain.config.Settings``.
This module keeps the PyQt UI and older imports working without committed secrets.
"""

from __future__ import annotations

from desain.config import get_settings

_settings = get_settings()

UNSPLASH_KEY = _settings.unsplash_access_key
DEFAULT_API_URL = _settings.llm_base_url
DEFAULT_API_KEY = _settings.llm_api_key
