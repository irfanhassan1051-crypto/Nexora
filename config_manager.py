"""
config_manager.py
=================
Configuration management for API keys and endpoint settings.
Persists settings in the current user's Nexora application data directory.
"""

import json
import os
from typing import Dict, Any

APP_DATA_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "Nexora"
)
CONFIG_FILE = os.path.join(APP_DATA_DIR, "app_settings.json")
LEGACY_CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "app_settings.json"
)

DEFAULT_CONFIG: Dict[str, Any] = {
    "provider": "gemini",
    "model": "gemini-3.8-flash",
    "onboarding_completed": False,
    "ollama_model": "llama3.2",
    "ollama_url": "http://localhost:11434/v1",
    "groq_api_key": "",
    "openrouter_api_key": "",
    "cerebras_api_key": "",
    "mistral_api_key": "",
    "gemini_api_key": "",
    "temperature": 0.7,
    "max_tokens": 4096
}

def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_FILE):
        if os.path.exists(LEGACY_CONFIG_FILE):
            try:
                with open(LEGACY_CONFIG_FILE, "r", encoding="utf-8") as f:
                    legacy_data = json.load(f)
            except (OSError, json.JSONDecodeError) as ex:
                raise RuntimeError(
                    f"Could not read existing Nexora settings from {LEGACY_CONFIG_FILE}: {ex}"
                ) from ex

            if not isinstance(legacy_data, dict):
                raise RuntimeError(
                    f"Existing Nexora settings in {LEGACY_CONFIG_FILE} must contain a JSON object."
                )
            merged = DEFAULT_CONFIG.copy()
            merged.update(legacy_data)
            save_config(merged)
            return merged

        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise RuntimeError(
                    f"Nexora settings in {CONFIG_FILE} must contain a JSON object."
                )
            merged = DEFAULT_CONFIG.copy()
            merged.update(data)
            return merged
    except (OSError, json.JSONDecodeError) as ex:
        raise RuntimeError(f"Could not read Nexora settings from {CONFIG_FILE}: {ex}") from ex

def save_config(cfg: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)
