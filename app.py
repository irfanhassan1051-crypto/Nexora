"""
app.py
======
Nexora is a desktop-style AI chat application using Streamlit and OpenAI-compatible APIs.
Phase 1: Local Offline Chat with Ollama.
"""

import streamlit as st
import openai
from providers import PROVIDERS, get_provider_config, get_client

# ---------------------------------------------------------
# Page Configuration (Desktop-style, clean layout)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Nexora",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Custom Styling for modern ChatGPT/Claude vibe
# ---------------------------------------------------------
st.markdown("""
<style>
    /* Clean desktop padding and header font */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 900px;
    }
    .stChatMessage {
        border-radius: 10px;
        margin-bottom: 0.5rem;
    }
    .provider-tag {
        font-size: 0.85rem;
        padding: 2px 8px;
        border-radius: 12px;
        background-color: #2e3846;
        color: #e0e0e0;
        display: inline-block;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Initialize Session State
# ---------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------
# Sidebar: Provider & Model Settings
# ---------------------------------------------------------
with st.sidebar:
    st.title("🤖 Chat Settings")
    st.caption("Configure your AI model & provider")

    # "New Chat" button to reset conversation
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    # Provider Dropdown
    provider_options = list(PROVIDERS.keys())
    selected_provider_key = st.selectbox(
        label="Select Provider",
        options=provider_options,
        index=0,  # Default to 'ollama'
        format_func=lambda key: PROVIDERS[key]["name"],
        help="Choose between offline Ollama or online API providers."
    )

    current_provider_config = get_provider_config(selected_provider_key)

    # Model Dropdown / Custom input
    models_list = current_provider_config.get("models", [])
    model_choice_options = models_list + ["Custom Model..."]
    
    selected_model_option = st.selectbox(
        label="Select Model",
        options=model_choice_options,
        index=0,
        help="Select a model or type a custom model name."
    )

    if selected_model_option == "Custom Model...":
        selected_model = st.text_input(
            label="Custom Model Name",
            value=current_provider_config.get("default_model", ""),
            placeholder="e.g. deepseek-r1, llama3.2:1b"
        )
    else:
        selected_model = selected_model_option

    st.divider()

    # Provider Information Card
    if current_provider_config["is_offline"]:
        st.success("🟢 **Offline Mode (Ollama)**\n\nRuns completely private on your local machine.")
        st.info(
            "💡 **Quick Check for Ollama:**\n\n"
            "1. Download Ollama from [ollama.com](https://ollama.com)\n"
            "2. Run in PowerShell:\n"
            f"   ```powershell\n   ollama run {selected_model}\n   ```\n"
            "3. Ready to chat offline!"
        )
    else:
        st.warning("🟡 **Phase 2 Ready (Online Provider)**")
        st.markdown(
            f"**Endpoint:** `{current_provider_config['base_url']}`\n\n"
            f"**Env Variable:** `{current_provider_config['env_key']}`\n\n"
            "To use this in Phase 2, add your API key in the `.env` file."
        )

    # History count
    st.divider()
    st.caption(f"💬 Messages in current chat: {len(st.session_state.messages)}")


# ---------------------------------------------------------
# Main Chat Area
# ---------------------------------------------------------
st.title("💬 Nexora")
st.caption(f"Connected to: **{current_provider_config['name']}** | Model: **`{selected_model}`**")

# Display previous conversation messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat Input Box
user_prompt = st.chat_input("Type your message here...")

if user_prompt:
    # 1. Append user prompt to session state and render
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # 2. Assistant response generation
    with st.chat_message("assistant"):
        # Create client for selected provider
        try:
            client = get_client(selected_provider_key)
        except ValueError as val_err:
            st.error(f"⚠️ **Configuration Notice:** {val_err}")
            st.stop()
        except Exception as e:
            st.error(f"⚠️ **Failed to initialize client:** {e}")
            st.stop()

        # Prepare messages payload for OpenAI-compatible endpoint
        payload_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ]

        # Call API and stream response
        try:
            with st.spinner("Thinking..."):
                response_stream = client.chat.completions.create(
                    model=selected_model,
                    messages=payload_messages,
                    stream=True
                )

            # Generator for streaming response chunks safely
            def stream_generator():
                for chunk in response_stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        content_piece = chunk.choices[0].delta.content
                        if content_piece:
                            yield content_piece

            # Stream response to UI
            assistant_reply = st.write_stream(stream_generator())

            # Save assistant reply to session state
            if assistant_reply:
                st.session_state.messages.append({"role": "assistant", "content": assistant_reply})

        except openai.APIConnectionError as conn_err:
            if current_provider_config["is_offline"]:
                st.error(
                    "⚠️ **Ollama-তে সংযোগ করা যাচ্ছে না (Connection Failed)!**\n\n"
                    "**সম্ভাব্য কারণ ও সমাধান:**\n"
                    "1. আপনার কম্পিউটারে **Ollama** কি চালু আছে? (Start menu থেকে Ollama অ্যাপ ওপেন করুন অথবা PowerShell-এ `ollama serve` চালান)।\n"
                    "2. নির্বাচিত মডেলটি কি আপনার লোকাল পিসিতে ডাউনলোড করা আছে? উদাহরণস্বরূপ, PowerShell-এ লিখুন:\n"
                    f"   ```powershell\n   ollama run {selected_model}\n   ```\n"
                    "3. লোকাল সার্ভার অ্যাড্রেস: `http://localhost:11434` নিশ্চিত করুন।"
                )
            else:
                st.error(
                    f"⚠️ **{current_provider_config['name']} এর সাথে সংযোগ স্থাপন করা যায়নি!**\n\n"
                    "দয়া করে আপনার ইন্টারনেট সংযোগ পরীক্ষা করুন।"
                )

        except openai.NotFoundError as not_found_err:
            st.error(
                f"⚠️ **Model Not Found (`{selected_model}`)!**\n\n"
                f"এই মডেলটি লোকাল Ollama-তে ইনস্টল করা নেই। ডাউনলোড করতে PowerShell-এ চালান:\n"
                f"```powershell\nollama pull {selected_model}\n```"
            )

        except openai.AuthenticationError as auth_err:
            st.error(
                f"🔑 **Authentication Failed!**\n\n"
                f"API Key সঠিক নয়। অনুগ্রহ করে `.env` ফাইলে `{current_provider_config.get('env_key')}` চেক করুন।"
            )

        except Exception as general_err:
            st.error(f"❌ **An unexpected error occurred:**\n\n`{str(general_err)}`")
