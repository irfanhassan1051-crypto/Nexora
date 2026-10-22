# Nexora

Nexora is an AI chat application with a native desktop interface for Windows, macOS, and Linux. Chat locally through Ollama or connect to supported online providers with your own API key. A Streamlit web interface is also included.

## Features

- Native PySide6 desktop chat interface with streaming responses and Markdown formatting.
- Local Ollama models for offline conversations after downloading a model.
- Online providers: Groq, Google Gemini, OpenRouter, Cerebras, and Mistral.
- Image attachments, with support depending on the selected model and provider.
- Persistent chat history, pinned conversations, and rename/delete controls.
- First-run setup for provider keys and optional Ollama installation.

## Run from source

### Requirements

- Python 3.10 or newer.
- For offline chat, install [Ollama](https://ollama.com/download) and download a model. Ollama is optional; online providers need their own API keys.

### Windows PowerShell

```powershell
git clone <your-repository-url>
cd Nexora
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python desktop_app.py
```

If PowerShell blocks virtual-environment activation, use the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe desktop_app.py
```

You can also run `Launch-Nexora.bat` after installing the dependencies.

### macOS or Linux

```bash
git clone <your-repository-url>
cd Nexora
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python desktop_app.py
```

## Provider setup and privacy

Enter online-provider API keys in Nexora's Settings. Keys and preferences are stored locally in the user's Nexora application-data directory. Do not commit API keys, `.env` files, local settings, or chat history.

For the optional Streamlit interface, copy `.env.example` to `.env`, add the provider keys you want to use, then run:

```powershell
python -m streamlit run app.py
```

Online providers receive the prompts and any images you send to them. Ollama runs models locally; downloading a model requires an internet connection, but local inference does not require an online provider key.

## Build the Windows desktop app

Install the build dependencies and build using the checked-in PyInstaller spec:

```powershell
pip install -r requirements-build.txt
pyinstaller --noconfirm Nexora.spec
```

The generated application is placed under `dist\Nexora\`. Build output and local data are intentionally excluded from Git. To distribute a Windows build, attach a packaged release to a GitHub Release rather than committing generated build folders.

## Project files

- `desktop_app.py` — native desktop application.
- `app.py` — Streamlit web interface.
- `llm_worker.py`, `providers.py` — provider/model integration.
- `database.py`, `config_manager.py` — local conversation and settings persistence.
- `assets/` — application icon resources.
- `Nexora.spec` — PyInstaller build configuration.

## License

No license has been selected for this project yet. Add a license before inviting others to reuse, modify, or redistribute the source.
