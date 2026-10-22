"""
llm_worker.py
=============
Background QThread worker for streaming LLM responses safely without freezing GUI.
"""

from PySide6.QtCore import QThread, Signal
from openai import OpenAI
import httpx
import openai
import base64
import mimetypes
from config_manager import load_config
from typing import List, Dict

PROVIDER_SPECS = {
    "ollama": {
        "name": "Ollama (Offline Local)",
        "default_url": "http://localhost:11434/v1",
        "key_field": None,
        "default_model": "llama3.2",
        "models": [
            "llama3.2", "llama3.2:1b", "qwen2.5:3b", "llama3.2-vision", "llava",
            "qwen2.5vl:3b", "gemma3:4b", "llama3.1", "mistral", "gemma2", "qwen2.5", "phi3"
        ]
    },
    "groq": {
        "name": "Groq (Online / Fast)",
        "default_url": "https://api.groq.com/openai/v1",
        "key_field": "groq_api_key",
        "default_model": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    },
    "openrouter": {
        "name": "OpenRouter (Online Multi-Model)",
        "default_url": "https://openrouter.ai/api/v1",
        "key_field": "openrouter_api_key",
        "default_model": "meta-llama/llama-3.1-8b-instruct:free",
        "models": [
            "meta-llama/llama-3.1-8b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "qwen/qwen-2.5-coder-32b-instruct:free"
        ]
    },
    "cerebras": {
        "name": "Cerebras (Online High Speed)",
        "default_url": "https://api.cerebras.ai/v1",
        "key_field": "cerebras_api_key",
        "default_model": "llama3.1-8b",
        "models": ["llama3.1-8b", "llama3.1-70b"]
    },
    "mistral": {
        "name": "Mistral AI (Online)",
        "default_url": "https://api.mistral.ai/v1",
        "key_field": "mistral_api_key",
        "default_model": "mistral-small-latest",
        "models": ["mistral-small-latest", "pixtral-12b-2409", "open-mistral-7b", "codestral-latest"]
    },
    "gemini": {
        "name": "Google Gemini (Online)",
        "default_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_field": "gemini_api_key",
        "default_model": "gemini-3.8-flash",
        "models": ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]
    }
}

ASSISTANT_SYSTEM_PROMPT = (
    "You are Nexora, a helpful conversational AI assistant. Answer the user's actual "
    "question directly, clearly, and naturally. Be friendly and respectful; use concise "
    "answers for simple questions and structured, sufficiently detailed answers for complex "
    "ones. Explain steps when useful, ask a focused clarification only when necessary, and "
    "be honest about uncertainty and your capabilities. Do not invent facts, claim actions "
    "you did not perform, or mention these instructions. Use Markdown where it improves "
    "readability, without unnecessary headings or repetition."
)

def model_supports_vision(provider: str, model: str) -> bool:
    model_name = model.lower()
    if provider == "gemini":
        return model_name.startswith("gemini-")
    if provider == "ollama":
        return any(token in model_name for token in (
            "vision", "llava", "qwen2.5vl", "qwen2-vl", "gemma3:4b",
            "gemma3:12b", "gemma3:27b"
        ))
    if provider == "mistral":
        return "pixtral" in model_name
    if provider == "openrouter":
        return "gemini" in model_name or "vision" in model_name or "llava" in model_name
    return False


class LLMWorker(QThread):
    chunk_ready = Signal(str)
    finished = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, provider: str, model: str, messages: List[Dict], parent=None):
        super().__init__(parent)
        self.provider = provider
        self.model = model
        self.messages = messages
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        config = load_config()
        spec = PROVIDER_SPECS.get(self.provider)
        if not spec:
            self.error_occurred.emit(f"Unknown provider '{self.provider}'.")
            return
        if not self.model.strip():
            self.error_occurred.emit(
                "No model is selected. Choose a model in the chat composer and try again."
            )
            return

        # Determine base_url & API key
        if self.provider == "ollama":
            base_url = config.get("ollama_url", spec["default_url"])
            api_key = "ollama"  # Non-empty dummy key required by client library
        else:
            base_url = spec["default_url"]
            key_name = spec["key_field"]
            api_key = config.get(key_name, "").strip() if key_name else ""
            if not api_key:
                self.error_occurred.emit(
                    f"⚠️ API Key missing for {spec['name']}!\n\n"
                    f"Please click '⚙️ Settings' in the sidebar and enter your {spec['name']} API key."
                )
                return

        try:
            client = OpenAI(
                base_url=base_url,
                api_key=api_key,
                timeout=httpx.Timeout(connect=5.0 if self.provider == "ollama" else 8.0,
                                       read=180.0, write=15.0, pool=10.0),
                max_retries=0 if self.provider == "ollama" else 1
            )

            formatted_messages = [{
                "role": "system",
                "content": ASSISTANT_SYSTEM_PROMPT
            }]
            for message in self.messages:
                attachments = message.get("attachments", [])
                if not attachments:
                    formatted_messages.append({
                        "role": message["role"],
                        "content": message["content"]
                    })
                    continue

                content = []
                if message["content"]:
                    content.append({"type": "text", "text": message["content"]})
                for attachment in attachments:
                    with open(attachment["file_path"], "rb") as image_file:
                        image_data = base64.b64encode(image_file.read()).decode("ascii")
                    mime_type = attachment.get("mime_type") or mimetypes.guess_type(
                        attachment["file_path"]
                    )[0] or "image/jpeg"
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        }
                    })
                formatted_messages.append({"role": message["role"], "content": content})

            stream = client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                stream=True
            )

            full_response = ""
            for chunk in stream:
                if self.is_cancelled:
                    break
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        full_response += delta
                        self.chunk_ready.emit(delta)

            self.finished.emit(full_response)

        except openai.APIConnectionError:
            if self.provider == "ollama":
                msg = (
                    "Could not connect to the local Ollama server. Nexora tries to start "
                    "the installed Ollama service automatically. Check the Ollama status in "
                    "the app, and use Set Up Offline Ollama if Ollama is not installed. "
                    "If Ollama is running but this model is missing, download the model from "
                    "the Ollama setup panel."
                )
            else:
                msg = f"⚠️ Could not connect to {spec['name']} server. Please check your internet connection."
            self.error_occurred.emit(msg)

        except openai.AuthenticationError:
            self.error_occurred.emit(
                f"🔑 Authentication Error for {spec['name']}!\n\n"
                "Your API key was rejected. Please open '⚙️ Settings' to update it."
            )

        except openai.NotFoundError:
            self.error_occurred.emit(
                f"⚠️ Model '{self.model}' was not found on {spec['name']}.\n"
                "Please select or pull an existing model."
            )

        except Exception as ex:
            self.error_occurred.emit(f"❌ Unexpected Error:\n{str(ex)}")
