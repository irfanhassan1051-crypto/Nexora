# 🚀 Nexora — Project Plan & Roadmap

## 💡 Project Overview
Nexora is an intelligent, desktop-style AI chat application built with **Streamlit** and Python. It delivers a seamless conversational experience that works **both offline (via local Ollama models)** and **online (using free and fast OpenAI-compatible API providers)**.

By leveraging the official `openai` Python SDK as a unified client, the app standardizes interactions across different AI engines without changing business logic.

---

## 🏗️ Architecture Design

```
+-------------------------------------------------------------+
|                     Streamlit Chat UI                       |
|           (st.chat_message, st.chat_input, Sidebar)         |
+-------------------------------------------------------------+
                              |
                              v
                 OpenAI-Compatible Client
                 (Unified API Specification)
                              |
        +---------------------+---------------------+
        |                                           |
        v                                           v
 [ Offline Engine ]                         [ Online Providers ]
  Ollama Local Server                        - Groq (LPU)
  http://localhost:11434/v1                  - OpenRouter
  (Private, No Internet)                     - Cerebras
                                             - Mistral AI
                                             - Google Gemini
```

---

## 🗺️ Development Roadmap

### 📍 Phase 1: Offline Chat (Ollama) [CURRENT STEP]
- [x] Basic project setup with virtual environment.
- [x] Unified provider configuration in `providers.py`.
- [x] Streamlit desktop-style chat UI (`st.chat_message`, `st.chat_input`).
- [x] Real-time streaming responses with `st.write_stream`.
- [x] Dynamic model selection and "New Chat" session reset.
- [x] In-memory chat history using `st.session_state`.
- [x] Resilient error handling (friendly message when Ollama is offline or model is missing).

---

### 📍 Phase 2: Online Providers Integration
- [ ] Read and validate API keys securely from `.env` using `python-dotenv`.
- [ ] Connect and test online providers:
  - **Groq**: Ultra-fast inference with Llama 3.3.
  - **OpenRouter**: Access to a broad spectrum of free community models.
  - **Cerebras**: Ultra-fast inference chips.
  - **Mistral AI**: Open-weight European LLMs (Mistral Small, Codestral).
  - **Google Gemini**: OpenAI-compatible endpoint (`/v1beta/openai/`).
- [ ] Dynamic model fetching per provider (querying provider endpoints or listing verified models).
- [ ] Token usage tracking and latency metrics per message.

---

### 📍 Phase 3: Persistent Chat History (SQLite)
- [ ] Replace ephemeral `st.session_state` with a local `sqlite3` database.
- [ ] Database Schema:
  - `conversations`: ID, title, created_at, provider, model.
  - `messages`: ID, conversation_id, role (user/assistant), content, timestamp, token_count.
- [ ] Sidebar conversation drawer:
  - Browse past chat threads.
  - Rename conversation titles (auto-generate title from first prompt).
  - Delete single thread or clear all conversations.
- [ ] Export conversation history (Markdown, JSON).

---

### 📍 Phase 4: Auto-Switch Offline/Online
- [ ] Automatic connectivity & latency health check:
  - Ping `http://localhost:11434` for Ollama availability.
  - Check internet access for cloud endpoints.
- [ ] Smart Fallback Strategy:
  - If offline: Automatically route queries to the local Ollama model.
  - If online: Option to switch to high-speed cloud providers or user-preferred provider.
- [ ] Desktop packaging (standalone executable or desktop shortcut launcher).

---

## 🔒 Security & Privacy Principles
1. **Never Hardcode Secrets**: All credentials live strictly in `.env`.
2. **Local First**: Completely functional without sending data outside the local machine when Ollama is selected.
3. **Safe Defaults**: Exclude `.env` and virtual environment files from version control via `.gitignore`.
