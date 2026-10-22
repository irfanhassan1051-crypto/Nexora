"""
providers.py
=============
AI Provider configurations and client factory.

All supported providers use OpenAI-compatible API specifications.
In Phase 1, 'ollama' is fully functional locally.
Other providers are configured and ready for Phase 2.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Configuration dictionary for all supported providers
PROVIDERS: Dict[str, Dict[str, Any]] = {
    "ollama": {
        "name": "Ollama (Offline / Local)",
        "base_url": "http://localhost:11434/v1",
        "env_key": None,  # No API key required for local Ollama
        "default_model": "llama3.2",
        "models": ["llama3.2", "llama3.1", "mistral", "gemma2", "qwen2.5", "phi3"],
        "is_offline": True,
        "description": "Runs completely offline on your local computer."
    },
    "groq": {
        "name": "Groq (Online / Fast)",
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "is_offline": False,
        "description": "Ultra-fast online inference via LPU."
    },
    "openrouter": {
        "name": "OpenRouter (Online / Multi-model)",
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "default_model": "meta-llama/llama-3.1-8b-instruct:free",
        "models": [
            "meta-llama/llama-3.1-8b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "qwen/qwen-2.5-coder-32b-instruct:free"
        ],
        "is_offline": False,
        "description": "Gateway to multiple free and paid LLM models."
    },
    "cerebras": {
        "name": "Cerebras (Online / High Speed)",
        "base_url": "https://api.cerebras.ai/v1",
        "env_key": "CEREBRAS_API_KEY",
        "default_model": "llama3.1-8b",
        "models": ["llama3.1-8b", "llama3.1-70b"],
        "is_offline": False,
        "description": "High-throughput AI chip inference."
    },
    "mistral": {
        "name": "Mistral AI (Online)",
        "base_url": "https://api.mistral.ai/v1",
        "env_key": "MISTRAL_API_KEY",
        "default_model": "mistral-small-latest",
        "models": ["mistral-small-latest", "open-mistral-7b", "codestral-latest"],
        "is_offline": False,
        "description": "European state-of-the-art open models."
    },
    "gemini": {
        "name": "Google Gemini (Online / OpenAI-compatible)",
        # Official Google Gemini OpenAI-compatible endpoint
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
        "default_model": "gemini-1.5-flash",
        "models": ["gemini-1.5-flash", "gemini-2.0-flash-exp", "gemini-1.5-pro"],
        "is_offline": False,
        "description": "Google Gemini models using OpenAI compatibility layer."
    }
}


def get_provider_config(provider_key: str) -> Dict[str, Any]:
    """
    Get the configuration dictionary for a given provider key.
    """
    if provider_key not in PROVIDERS:
        raise ValueError(f"Unknown provider: '{provider_key}'. Available: {list(PROVIDERS.keys())}")
    return PROVIDERS[provider_key]


def get_client(provider_key: str) -> OpenAI:
    """
    Initializes and returns an OpenAI client configured for the selected provider.
    
    - For 'ollama', api_key is set to a dummy 'ollama' string because the client library
      requires a non-empty string, but the local Ollama server ignores it.
    - For other providers, reads the corresponding API key from environment variables (.env).
    """
    config = get_provider_config(provider_key)
    base_url = config["base_url"]
    
    if config["is_offline"]:
        # Ollama does not need a real API key, but OpenAI client needs non-empty string
        api_key = "ollama"
    else:
        env_var_name = config.get("env_key")
        api_key = os.getenv(env_var_name) if env_var_name else None
        if not api_key:
            raise ValueError(
                f"API Key not found for {config['name']}! "
                f"Please set '{env_var_name}' in your .env file."
            )

    return OpenAI(
        base_url=base_url,
        api_key=api_key
    )

