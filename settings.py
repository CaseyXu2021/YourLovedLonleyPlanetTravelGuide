"""Central configuration.

Secrets are never hard-coded in source. Resolution order:

1. Environment variable (e.g. ``AZURE_OPENAI_API_KEY``)
2. Streamlit secrets (``st.secrets`` / ``.streamlit/secrets.toml``)

Locally, put the keys in ``.streamlit/secrets.toml`` (git-ignored).
On Streamlit Community Cloud, paste the same TOML into
"Advanced settings -> Secrets".
"""

from __future__ import annotations

import os
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent


def get_secret(name: str, default: str = "") -> str:
    """Return a secret from env vars, then Streamlit secrets, then ``default``."""
    value = os.environ.get(name)
    if value:
        return value

    try:  # Streamlit runtime
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass

    try:  # Non-Streamlit contexts (tests, scripts)
        import tomllib

        secrets_file = _APP_DIR / ".streamlit" / "secrets.toml"
        if secrets_file.exists():
            with open(secrets_file, "rb") as fh:
                data = tomllib.load(fh)
            if name in data:
                return str(data[name])
    except Exception:
        pass

    return default


# --- Azure OpenAI (HKUST gateway) --------------------------------------------
AZURE_API_KEY = get_secret("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = get_secret("AZURE_OPENAI_ENDPOINT", "https://hkust.azure-api.net")
AZURE_DEPLOYMENT_NAME = get_secret("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_API_VERSION = get_secret("AZURE_OPENAI_API_VERSION", "2024-10-21")

# --- Optional third-party image APIs -----------------------------------------
OUTSCRAPER_API_KEY = get_secret("OUTSCRAPER_API_KEY")
UNSPLASH_ACCESS_KEY = get_secret("UNSPLASH_ACCESS_KEY")
PIXABAY_API_KEY = get_secret("PIXABAY_API_KEY")


__all__ = [
    "AZURE_API_KEY",
    "AZURE_ENDPOINT",
    "AZURE_DEPLOYMENT_NAME",
    "AZURE_API_VERSION",
    "OUTSCRAPER_API_KEY",
    "UNSPLASH_ACCESS_KEY",
    "PIXABAY_API_KEY",
    "get_secret",
]
