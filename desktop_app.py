"""
desktop_app.py
==============
Native Desktop GUI Application for AI Chat (Offline & Online).
Built with PySide6 (Qt) for Windows, macOS, and Linux.
"""

import sys
import os
import json
import shutil
import uuid
from datetime import datetime
import urllib.error
import urllib.request
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QTextBrowser,
    QScrollArea, QFrame, QSplitter, QListWidget, QListWidgetItem,
    QDialog, QLineEdit, QFormLayout, QMessageBox, QSizePolicy,
    QToolButton, QMenu, QFileDialog, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QTimer, QProcess
from PySide6.QtGui import (
    QFont, QColor, QPalette, QKeyEvent, QIcon, QDesktopServices, QTextCursor,
    QImageReader, QImageWriter, QPixmap
)
from PySide6.QtCore import QUrl

import database
from config_manager import load_config, save_config
from llm_worker import LLMWorker, PROVIDER_SPECS, model_supports_vision

APP_RESOURCE_DIR = getattr(
    sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))
)
APP_ICON_PATH = os.path.join(APP_RESOURCE_DIR, "assets", "Nexora-icon.jpg")

MAX_ATTACHMENTS = 4
MAX_IMAGE_FILE_SIZE = 20 * 1024 * 1024
MAX_IMAGE_DIMENSION = 1536


def save_image_attachment(source_path):
    if os.path.getsize(source_path) > MAX_IMAGE_FILE_SIZE:
        raise ValueError(f"{os.path.basename(source_path)} is larger than 20 MB.")

    reader = QImageReader(source_path)
    reader.setAutoTransform(True)
    image_size = reader.size()
    if image_size.isValid():
        if (
            image_size.width() > 20000
            or image_size.height() > 20000
            or image_size.width() * image_size.height() > 50_000_000
        ):
            raise ValueError(f"{os.path.basename(source_path)} has unsupported dimensions.")
        if max(image_size.width(), image_size.height()) > MAX_IMAGE_DIMENSION:
            reader.setScaledSize(image_size.scaled(
                MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION, Qt.KeepAspectRatio
            ))
    image = reader.read()
    if image.isNull():
        raise ValueError(f"Could not read image {os.path.basename(source_path)}.")

    os.makedirs(database.ATTACHMENTS_DIR, exist_ok=True)
    stored_path = os.path.join(database.ATTACHMENTS_DIR, f"{uuid.uuid4().hex}.jpg")
    writer = QImageWriter(stored_path, b"jpeg")
    writer.setQuality(86)
    if not writer.write(image):
        raise OSError(f"Could not save image attachment: {writer.errorString()}")
    return {
        "name": os.path.basename(source_path),
        "file_path": stored_path,
        "mime_type": "image/jpeg"
    }

# ------------------------------------------------------------------------------
# Modern Dark QSS Theme
# ------------------------------------------------------------------------------
DARK_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #212121;
    color: #ececec;
    font-family: 'Segoe UI', 'SF Pro Display', Helvetica, Arial, sans-serif;
    font-size: 14px;
}

QWidget {
    color: #f4f4f5;
}

/* Sidebar Styling */
#sidebar {
    background-color: #171717;
    border: none;
    padding: 8px;
}

#toolRail {
    background-color: #171717;
    border-right: 1px solid #292929;
}

#brandTitle {
    font-size: 16px;
    font-weight: 700;
    color: #ececec;
    padding: 8px 4px;
}

#newChatBtn {
    background-color: #262626;
    color: #ececec;
    font-weight: 600;
    border: 1px solid #363636;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 13px;
    text-align: left;
}
#newChatBtn:hover {
    background-color: #333333;
}

#sectionHeader {
    font-size: 12px;
    font-weight: 600;
    color: #929292;
    margin-top: 15px;
    margin-bottom: 5px;
}

QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}

QListWidget::item {
    background-color: transparent;
    color: #c5c5c5;
    padding: 8px;
    border-radius: 7px;
    margin-bottom: 2px;
}

QListWidget::item:hover {
    background-color: #252525;
    color: #ffffff;
}

QListWidget::item:selected {
    background-color: #303030;
    color: #ffffff;
}

/* Dropdowns & Inputs */
QComboBox {
    background-color: #262626;
    color: #ececec;
    border: 1px solid #3a3a3a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #262626;
    color: #ececec;
    selection-background-color: #3a3a3a;
    border: 1px solid #3a3a3a;
}

#settingsBtn {
    background-color: transparent;
    color: #c5c5c5;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 8px 12px;
    font-weight: 500;
}
#settingsBtn:hover {
    background-color: #282828;
}

/* Chat Central Area */
#chatHeader {
    background-color: #212121;
    border-bottom: 1px solid #292929;
    padding: 8px 16px;
}

#chatTitle {
    font-size: 16px;
    font-weight: 600;
    color: #ececec;
}

#headerAction {
    background-color: transparent;
    color: #c5c5c5;
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 6px 9px;
}

#headerAction:hover {
    background-color: #303030;
}

#statusBadge {
    background-color: #262626;
    color: #a8a8a8;
    font-size: 12px;
    font-weight: 600;
    border-radius: 12px;
    padding: 3px 10px;
    border: 1px solid #393939;
}

#scrollArea {
    background-color: #212121;
    border: none;
}

#messagesContainer {
    background-color: #212121;
}

#assistantResponse {
    background-color: transparent;
    border: none;
}

#outgoingBubble {
    background-color: #303030;
    border: none;
    border-radius: 20px;
}

/* Chat Composer */
#inputFrame {
    background-color: #212121;
    padding: 8px 24px 12px;
}

#composerCard {
    background-color: #303030;
    border: 1px solid #414141;
    border-radius: 26px;
}

#chatInput {
    background-color: transparent;
    color: #ececec;
    border: none;
    padding: 10px 14px 2px;
    font-size: 15px;
}

#composerIconButton {
    background-color: transparent;
    color: #d5d5d5;
    border: none;
    border-radius: 18px;
    min-width: 36px;
    min-height: 36px;
    font-size: 20px;
}
#composerIconButton:hover:enabled {
    background-color: #454545;
}
#composerIconButton:disabled {
    color: #777777;
}

#composerModelCombo {
    background-color: transparent;
    color: #c5c5c5;
    border: none;
    padding: 7px 8px;
    font-size: 13px;
}

#composerModelCombo QLineEdit {
    background-color: transparent;
    color: #c5c5c5;
    border: none;
    padding: 0;
}

#composerSendBtn {
    background-color: #f4f4f4;
    color: #212121;
    border: none;
    border-radius: 18px;
    min-width: 36px;
    min-height: 36px;
    font-size: 20px;
    font-weight: 700;
}
#composerSendBtn:hover:enabled {
    background-color: #d5d5d5;
}
#composerSendBtn:disabled {
    background-color: #525252;
    color: #a1a1aa;
}

QScrollBar:vertical {
    border: none;
    background: #212121;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #4a4a4a;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #666666;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

# ------------------------------------------------------------------------------
# Custom Multi-line Input with Enter to Send
# ------------------------------------------------------------------------------
class ChatInputEdit(QTextEdit):
    sendRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("How can I help you today?")
        self.setFixedHeight(64)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.sendRequested.emit()
        else:
            super().keyPressEvent(event)

# ------------------------------------------------------------------------------
# Message Widget (renders user or assistant card)
# ------------------------------------------------------------------------------
class MessageCard(QWidget):
    def __init__(
        self,
        role: str,
        content: str = "",
        attachments=None,
        timestamp: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.role = role
        self.content = content

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 3, 8, 3)
        row.setSpacing(0)
        self.bubble = QFrame()
        self.bubble.setObjectName("outgoingBubble" if role == "user" else "assistantResponse")
        self.bubble.setMaximumWidth(1200)
        if role == "user":
            self.bubble.setMaximumWidth(760)
        if role != "user":
            self.bubble.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            self.bubble.setStyleSheet("QFrame { background-color: transparent; border: none; }")
        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 6)
        bubble_layout.setSpacing(3)

        if role == "user":
            sender_label = QLabel("You")
            sender_label.setStyleSheet("color: #bcbcbc; font-size: 11px; font-weight: 600;")
            bubble_layout.addWidget(sender_label)

        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                background: transparent;
                color: #e9edef;
                border: none;
                padding: 0;
                font-size: 14px;
            }
        """)

        self.set_content(content)
        bubble_layout.addWidget(self.text_browser)
        for attachment in attachments or []:
            image_label = QLabel()
            image_label.setToolTip(attachment.get("name", "Image attachment"))
            image = QPixmap(attachment.get("file_path", ""))
            if image.isNull():
                image_label.setText("Image unavailable")
                image_label.setStyleSheet("color: #a1a1aa;")
            else:
                image_label.setPixmap(image.scaled(
                    280, 210, Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            bubble_layout.addWidget(
                image_label, 0, Qt.AlignRight if role == "user" else Qt.AlignLeft
            )

        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignRight)
        self.time_label.setStyleSheet("color: #8696a0; font-size: 10px;")
        bubble_layout.addWidget(self.time_label)
        self.set_timestamp(timestamp)

        if role != "user":
            self.time_label.hide()
            self.copy_button = QToolButton()
            self.copy_button.setText("Copy")
            self.copy_button.setToolTip("Copy this answer")
            self.copy_button.setStyleSheet(
                "QToolButton { color: #a8a8a8; background: transparent; border: none; "
                "padding: 3px 5px; font-size: 11px; }"
                "QToolButton:hover { color: #eeeeee; background: #303030; border-radius: 5px; }"
            )
            self.copy_button.clicked.connect(
                lambda: QApplication.clipboard().setText(self.content)
            )
            bubble_layout.addWidget(self.copy_button, 0, Qt.AlignLeft)

        if role == "user":
            row.addStretch(1)
            row.addWidget(self.bubble, 0, Qt.AlignRight | Qt.AlignBottom)
        else:
            row.addWidget(self.bubble, 1, Qt.AlignBottom)

    def set_timestamp(self, timestamp: str):
        self.time_label.setText(timestamp[11:16] if len(timestamp) >= 16 else "")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "text_browser"):
            document = self.text_browser.document()
            document.setTextWidth(max(1, self.text_browser.viewport().width()))
            document.adjustSize()
            height = max(55, int(document.size().height()) + 8)
            if self.text_browser.height() != height:
                self.text_browser.setFixedHeight(height)

    def set_content(self, text: str):
        self.content = text
        self.text_browser.setMarkdown(text)
        self.text_browser.document().adjustSize()
        doc_height = int(self.text_browser.document().size().height()) + 8
        self.text_browser.setFixedHeight(max(55, doc_height))

# ------------------------------------------------------------------------------
# Settings Dialog (Configures API keys and local endpoint)
# ------------------------------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, parent=None, first_run=False):
        super().__init__(parent)
        self.first_run = first_run
        self.setWindowTitle("Welcome to Nexora — First-run Setup" if first_run else "Settings — API Keys & Endpoints")
        self.setMinimumWidth(560)
        self.setStyleSheet(DARK_THEME_QSS)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        info_text = (
            "Set up online AI providers with your own API keys. You can skip keys and use Ollama locally instead. "
            "After saving, Nexora can guide you through installing Ollama and a local model."
            if first_run else
            "Configure your API keys for online providers or your local Ollama address:"
        )
        info_lbl = QLabel(info_text)
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #a1a1aa; font-size: 13px;")
        layout.addWidget(info_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        cfg = load_config()

        self.ollama_edit = QLineEdit(cfg.get("ollama_url", "http://localhost:11434/v1"))
        self.groq_edit = QLineEdit(cfg.get("groq_api_key", ""))
        self.groq_edit.setEchoMode(QLineEdit.Password)
        self.gemini_edit = QLineEdit(cfg.get("gemini_api_key", ""))
        self.gemini_edit.setEchoMode(QLineEdit.Password)
        self.openrouter_edit = QLineEdit(cfg.get("openrouter_api_key", ""))
        self.openrouter_edit.setEchoMode(QLineEdit.Password)
        self.cerebras_edit = QLineEdit(cfg.get("cerebras_api_key", ""))
        self.cerebras_edit.setEchoMode(QLineEdit.Password)
        self.mistral_edit = QLineEdit(cfg.get("mistral_api_key", ""))
        self.mistral_edit.setEchoMode(QLineEdit.Password)

        for w in [self.ollama_edit, self.groq_edit, self.gemini_edit, self.openrouter_edit, self.cerebras_edit, self.mistral_edit]:
            w.setStyleSheet("background-color: #27272a; border: 1px solid #3f3f46; border-radius: 6px; padding: 6px; color: #fff;")

        form.addRow("Local Ollama Server URL:", self.ollama_edit)
        form.addRow("Groq API Key:", self.groq_edit)
        form.addRow("Google Gemini API Key:", self.gemini_edit)
        form.addRow("OpenRouter API Key:", self.openrouter_edit)
        form.addRow("Cerebras API Key:", self.cerebras_edit)
        form.addRow("Mistral AI API Key:", self.mistral_edit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Skip setup for now" if first_run else "Cancel")
        cancel_btn.clicked.connect(self.skip_first_run if first_run else self.reject)
        cancel_btn.setStyleSheet("background-color: #27272a; border: 1px solid #3f3f46; border-radius: 6px; padding: 8px 16px;")

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_and_close)
        save_btn.setStyleSheet("background-color: #2563eb; color: #fff; font-weight: bold; border-radius: 6px; padding: 8px 16px;")

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def save_and_close(self):
        cfg = load_config()
        cfg["ollama_url"] = self.ollama_edit.text().strip()
        cfg["groq_api_key"] = self.groq_edit.text().strip()
        cfg["gemini_api_key"] = self.gemini_edit.text().strip()
        cfg["openrouter_api_key"] = self.openrouter_edit.text().strip()
        cfg["cerebras_api_key"] = self.cerebras_edit.text().strip()
        cfg["mistral_api_key"] = self.mistral_edit.text().strip()
        save_config(cfg)
        self.accept()

    def skip_first_run(self):
        cfg = load_config()
        cfg["onboarding_completed"] = True
        save_config(cfg)
        self.reject()


class OllamaSetupDialog(QDialog):
    OLLAMA_DOWNLOAD_URL = "https://ollama.com/download/windows"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set up Ollama for offline chat")
        self.setMinimumSize(560, 440)
        self.setStyleSheet(DARK_THEME_QSS)
        self.available_models = []
        self.process = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        intro = QLabel(
            "Ollama runs AI models on your computer. Install Ollama, return here, check the connection, "
            "then download a model once. Model downloads need internet; using a downloaded model can be offline."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #a1a1aa;")
        layout.addWidget(intro)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.download_ollama_btn = QPushButton("Download Ollama from the official website")
        self.download_ollama_btn.setObjectName("settingsBtn")
        self.download_ollama_btn.clicked.connect(self.open_download_page)
        layout.addWidget(self.download_ollama_btn)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Local model"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems([
            "llama3.2", "llama3.2:1b", "qwen2.5:3b", "gemma3:1b",
            "llama3.2-vision", "qwen2.5vl:3b", "gemma3:4b"
        ])
        self.model_combo.setCurrentText(load_config().get("ollama_model", "llama3.2"))
        self.model_combo.currentTextChanged.connect(self.update_selected_model)
        model_row.addWidget(self.model_combo, 1)
        layout.addLayout(model_row)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Model download progress will appear here.")
        self.output.setMaximumHeight(140)
        layout.addWidget(self.output)

        actions = QHBoxLayout()
        self.check_btn = QPushButton("Check Ollama")
        self.check_btn.clicked.connect(self.check_connection)
        actions.addWidget(self.check_btn)

        self.pull_btn = QPushButton("Download model")
        self.pull_btn.clicked.connect(self.pull_model)
        actions.addWidget(self.pull_btn)

        self.use_btn = QPushButton("Use offline model")
        self.use_btn.setObjectName("newChatBtn")
        self.use_btn.setEnabled(False)
        self.use_btn.clicked.connect(self.use_model)
        actions.addWidget(self.use_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        actions.addWidget(close_btn)
        layout.addLayout(actions)

        self.check_connection()

    def ollama_api_base(self):
        configured_url = load_config().get("ollama_url", "http://localhost:11434/v1").strip().rstrip("/")
        if configured_url.endswith("/v1"):
            configured_url = configured_url[:-3]
        return configured_url

    def open_download_page(self):
        if not QDesktopServices.openUrl(QUrl(self.OLLAMA_DOWNLOAD_URL)):
            QMessageBox.warning(
                self,
                "Could not open browser",
                f"Open this official Ollama download page manually:\n{self.OLLAMA_DOWNLOAD_URL}"
            )

    def check_connection(self):
        self.use_btn.setEnabled(False)
        tags_url = f"{self.ollama_api_base()}/api/tags"
        request = urllib.request.Request(tags_url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            ValueError,
            TypeError,
            UnicodeDecodeError,
            json.JSONDecodeError
        ):
            self.available_models = []
            self.status_label.setText(
                "Ollama is not reachable yet. Install it from the official website above, leave it running, "
                "then return here and click Check Ollama."
            )
            self.status_label.setStyleSheet("color: #fbbf24;")
            self.pull_btn.setEnabled(False)
            return

        if not isinstance(data, dict) or not isinstance(data.get("models", []), list):
            self.status_label.setText("Ollama responded with an unexpected model list.")
            self.status_label.setStyleSheet("color: #f87171;")
            self.pull_btn.setEnabled(False)
            return

        self.available_models = [
            model.get("name", "")
            for model in data["models"]
            if isinstance(model, dict) and model.get("name")
        ]
        selected_model = self.model_combo.currentText().strip()
        existing_options = {
            self.model_combo.itemText(index)
            for index in range(self.model_combo.count())
        }
        for model in self.available_models:
            if model not in existing_options:
                self.model_combo.addItem(model)

        if self.available_models:
            self.status_label.setText(
                "Ollama is running. Installed models: " + ", ".join(self.available_models)
            )
            self.status_label.setStyleSheet("color: #34d399;")
        else:
            self.status_label.setText(
                "Ollama is running, but no models are installed. Choose one and click Download model."
            )
            self.status_label.setStyleSheet("color: #fbbf24;")
        self.model_combo.setCurrentText(selected_model)
        self.pull_btn.setEnabled(True)
        self.update_selected_model(selected_model)

    def update_selected_model(self, model):
        self.use_btn.setEnabled(self.is_model_installed(model))

    def is_model_installed(self, model):
        model = model.strip()
        return (
            model in self.available_models
            or (":" not in model and f"{model}:latest" in self.available_models)
        )

    def pull_model(self):
        model = self.model_combo.currentText().strip()
        if not model:
            QMessageBox.warning(self, "Model required", "Enter a model name to download.")
            return

        executable = shutil.which("ollama")
        if not executable:
            self.status_label.setText(
                "The Ollama server responded, but the ollama command was not found. "
                "Finish installing Ollama and reopen Nexora, then try again."
            )
            self.status_label.setStyleSheet("color: #fbbf24;")
            return

        self.output.clear()
        self.pull_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.use_btn.setEnabled(False)
        self.status_label.setText(f"Downloading {model}. Keep Nexora open until the download completes.")
        self.status_label.setStyleSheet("color: #93c5fd;")

        self.process = QProcess(self)
        self.process.setProgram(executable)
        self.process.setArguments(["pull", model])
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_pull_output)
        self.process.finished.connect(self.on_pull_finished)
        self.process.errorOccurred.connect(self.on_pull_error)
        self.process.start()

    def read_pull_output(self):
        if self.process:
            text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
            self.output.moveCursor(QTextCursor.End)
            self.output.insertPlainText(text)
            self.output.ensureCursorVisible()

    def on_pull_finished(self, exit_code, _exit_status):
        self.read_pull_output()
        self.pull_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        if exit_code == 0:
            self.status_label.setText("Model download finished. Checking the Ollama model list…")
            self.status_label.setStyleSheet("color: #34d399;")
            self.check_connection()
        else:
            self.status_label.setText(
                f"Model download failed (exit code {exit_code}). Check the output above and try again."
            )
            self.status_label.setStyleSheet("color: #f87171;")

    def on_pull_error(self, _error):
        self.pull_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        self.status_label.setText(
            "Could not start the Ollama download command. Confirm Ollama is installed, then reopen Nexora."
        )
        self.status_label.setStyleSheet("color: #f87171;")

    def use_model(self):
        model = self.model_combo.currentText().strip()
        if not self.is_model_installed(model):
            QMessageBox.warning(self, "Model not installed", "Download this model before selecting it for offline chat.")
            return

        config = load_config()
        config["provider"] = "ollama"
        config["model"] = model
        config["ollama_model"] = model
        save_config(config)
        self.accept()

# ------------------------------------------------------------------------------
# Main Application Window
# ------------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nexora")
        self.setWindowIcon(QIcon(APP_ICON_PATH))
        self.resize(1100, 750)
        self.setMinimumSize(850, 580)
        self.setStyleSheet(DARK_THEME_QSS)

        self.current_conversation_id = None
        self.worker = None
        self.current_assistant_card = None
        self.accumulated_response = ""
        self.pending_images = []
        self.ollama_process = None
        self.ollama_start_attempts = 0
        self.ollama_start_error = ""
        self.shutting_down = False

        self.init_ui()
        self.load_conversations_list()
        QTimer.singleShot(500, self.ensure_ollama_running)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Splitter between sidebar and chat area
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # -----------------------------
        # Left Sidebar Widget
        # -----------------------------
        navigation_panel = QWidget()
        navigation_panel.setMinimumWidth(260)
        navigation_panel.setMaximumWidth(300)
        navigation_layout = QHBoxLayout(navigation_panel)
        navigation_layout.setContentsMargins(0, 0, 0, 0)
        navigation_layout.setSpacing(0)

        tool_rail = QWidget()
        tool_rail.setObjectName("toolRail")
        tool_rail.setFixedWidth(48)
        tool_rail_layout = QVBoxLayout(tool_rail)
        tool_rail_layout.setContentsMargins(5, 8, 5, 8)
        tool_rail_layout.setSpacing(6)

        def add_rail_button(label, tooltip, callback):
            button = QToolButton()
            button.setText(label)
            button.setToolTip(tooltip)
            button.setAccessibleName(tooltip)
            button.setFixedSize(36, 36)
            button.setStyleSheet(
                "QToolButton { color: #d4d4d4; background: transparent; border: none; "
                "border-radius: 8px; font-size: 17px; }"
                "QToolButton:hover { background: #303030; }"
            )
            button.clicked.connect(callback)
            tool_rail_layout.addWidget(button)
            return button

        add_rail_button("⌂", "New chat", self.start_new_chat)
        add_rail_button("◷", "Recent chats", lambda: self.history_list.setFocus())
        tool_rail_layout.addStretch()
        add_rail_button("⚙", "Settings and API keys", self.open_settings)
        add_rail_button("◉", "Set up offline Ollama", self.open_ollama_setup)
        navigation_layout.addWidget(tool_rail)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(212)
        sidebar.setMaximumWidth(252)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(7)
        navigation_layout.addWidget(sidebar, 1)

        brand_lbl = QLabel("Nexora  ⌄")
        brand_lbl.setObjectName("brandTitle")
        sidebar_layout.addWidget(brand_lbl)

        # "New Chat" primary button
        new_chat_btn = QPushButton("＋  New chat")
        new_chat_btn.setObjectName("newChatBtn")
        new_chat_btn.clicked.connect(self.start_new_chat)
        sidebar_layout.addWidget(new_chat_btn)

        # Chat History List
        history_hdr = QLabel("Your chats")
        history_hdr.setObjectName("sectionHeader")
        sidebar_layout.addWidget(history_hdr)

        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.on_conversation_selected)
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(
            self.show_conversation_context_menu
        )
        sidebar_layout.addWidget(self.history_list)

        sidebar_layout.addStretch()

        # Provider Selection
        provider_hdr = QLabel("AI PROVIDER")
        provider_hdr.setObjectName("sectionHeader")
        sidebar_layout.addWidget(provider_hdr)

        self.provider_combo = QComboBox()
        for p_key, p_spec in PROVIDER_SPECS.items():
            self.provider_combo.addItem(p_spec["name"], p_key)
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        sidebar_layout.addWidget(self.provider_combo)

        self.model_combo = QComboBox()
        self.model_combo.setObjectName("composerModelCombo")
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(170)
        self.model_combo.setMaximumWidth(280)
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)

        settings_btn = QPushButton("⚙  Settings & API keys")
        settings_btn.setObjectName("settingsBtn")
        settings_btn.clicked.connect(self.open_settings)
        sidebar_layout.addWidget(settings_btn)

        ollama_setup_btn = QPushButton("◉  Set up offline Ollama")
        ollama_setup_btn.setObjectName("settingsBtn")
        ollama_setup_btn.clicked.connect(self.open_ollama_setup)
        sidebar_layout.addWidget(ollama_setup_btn)

        splitter.addWidget(navigation_panel)

        # -----------------------------
        # Right Chat Area
        # -----------------------------
        chat_container = QWidget()
        self.chat_container = chat_container
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        # Header Bar
        header_frame = QFrame()
        header_frame.setObjectName("chatHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 10, 20, 10)

        self.chat_title_lbl = QLabel("New Conversation")
        self.chat_title_lbl.setObjectName("chatTitle")
        header_layout.addWidget(self.chat_title_lbl)

        header_layout.addStretch()

        share_btn = QPushButton("Share")
        share_btn.setObjectName("headerAction")
        share_btn.clicked.connect(self.copy_conversation)
        header_layout.addWidget(share_btn)

        more_btn = QToolButton()
        more_btn.setObjectName("headerAction")
        more_btn.setText("•••")
        more_btn.setToolTip("More chat options")
        more_menu = QMenu(more_btn)
        copy_action = more_menu.addAction("Copy conversation")
        copy_action.triggered.connect(self.copy_conversation)
        delete_action = more_menu.addAction("Delete conversation")
        delete_action.triggered.connect(self.delete_current_conversation)
        more_btn.setMenu(more_menu)
        more_btn.setPopupMode(QToolButton.InstantPopup)
        header_layout.addWidget(more_btn)

        self.status_badge = QLabel("🟢 Ready")
        self.status_badge.setObjectName("statusBadge")
        header_layout.addWidget(self.status_badge)

        chat_layout.addWidget(header_frame)

        # Scrollable Messages Display Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("scrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.messages_widget = QWidget()
        self.messages_widget.setObjectName("messagesContainer")
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(24, 18, 24, 18)
        self.messages_layout.setSpacing(16)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_widget)
        chat_layout.addWidget(self.scroll_area)

        # Chat composer
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_frame.setMaximumHeight(300)
        input_frame_layout = QVBoxLayout(input_frame)
        input_frame_layout.setContentsMargins(0, 0, 0, 0)
        input_frame_layout.setSpacing(4)

        disclaimer = QLabel("Nexora can make mistakes. Check important information.")
        disclaimer.setAlignment(Qt.AlignCenter)
        disclaimer.setStyleSheet("color: #8e8e8e; font-size: 11px; padding: 2px;")
        input_frame_layout.addWidget(disclaimer)

        composer_card = QFrame()
        self.composer_card = composer_card
        composer_card.setObjectName("composerCard")
        composer_card.setMaximumWidth(780)
        composer_card.setMaximumHeight(260)
        composer_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        composer_layout = QVBoxLayout(composer_card)
        composer_layout.setContentsMargins(10, 8, 10, 8)
        composer_layout.setSpacing(2)

        self.chat_input = ChatInputEdit()
        self.chat_input.setObjectName("chatInput")
        self.chat_input.sendRequested.connect(self.send_message)
        composer_layout.addWidget(self.chat_input)

        self.draft_images_widget = QWidget()
        self.draft_images_layout = QHBoxLayout(self.draft_images_widget)
        self.draft_images_layout.setContentsMargins(8, 4, 8, 4)
        self.draft_images_layout.setSpacing(8)
        self.draft_images_widget.hide()
        composer_layout.addWidget(self.draft_images_widget)

        self.attachment_notice = QLabel(
            "Images stay on this device for Ollama. Online providers receive images you send."
        )
        self.attachment_notice.setStyleSheet("color: #a1a1aa; font-size: 11px; padding-left: 8px;")
        self.attachment_notice.setWordWrap(True)
        self.attachment_notice.hide()
        composer_layout.addWidget(self.attachment_notice)

        composer_toolbar = QHBoxLayout()
        composer_toolbar.setContentsMargins(2, 0, 2, 0)
        composer_toolbar.setSpacing(4)

        self.attach_btn = QToolButton()
        self.attach_btn.setObjectName("composerIconButton")
        self.attach_btn.setText("+")
        self.attach_btn.setToolTip("Attach images (up to 4)")
        self.attach_btn.clicked.connect(self.add_images)
        composer_toolbar.addWidget(self.attach_btn)
        composer_toolbar.addStretch()
        composer_toolbar.addWidget(self.model_combo)

        self.mic_btn = QToolButton()
        self.mic_btn.setObjectName("composerIconButton")
        self.mic_btn.setText("♩")
        self.mic_btn.setToolTip("Voice input is not available yet")
        self.mic_btn.setEnabled(False)
        composer_toolbar.addWidget(self.mic_btn)

        self.send_btn = QToolButton()
        self.send_btn.setObjectName("composerSendBtn")
        self.send_btn.setText("↑")
        self.send_btn.setToolTip("Send message")
        self.send_btn.clicked.connect(self.send_message)
        composer_toolbar.addWidget(self.send_btn)

        self.stop_btn = QToolButton()
        self.stop_btn.setObjectName("composerIconButton")
        self.stop_btn.setText("■")
        self.stop_btn.setToolTip("Stop generating")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_generation)
        self.stop_btn.hide()
        composer_toolbar.addWidget(self.stop_btn)

        composer_layout.addLayout(composer_toolbar)
        composer_row = QHBoxLayout()
        composer_row.addStretch()
        composer_row.addWidget(composer_card)
        composer_row.addStretch()
        input_frame_layout.addLayout(composer_row)
        chat_layout.addWidget(input_frame)

        splitter.addWidget(chat_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([276, 900])

        # Apply saved config
        cfg = load_config()
        p_idx = self.provider_combo.findData(cfg.get("provider", "ollama"))
        if p_idx >= 0:
            self.provider_combo.setCurrentIndex(p_idx)
        self.on_provider_changed()
        QTimer.singleShot(250, self.show_first_run_setup)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self.update_composer_width)

    def update_composer_width(self):
        if hasattr(self, "composer_card") and hasattr(self, "chat_container"):
            composer_width = min(780, max(360, int(self.chat_container.width() * 0.62)))
            self.composer_card.setFixedWidth(composer_width)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.on_provider_changed()

    def ollama_api_base(self):
        configured_url = load_config().get(
            "ollama_url", "http://localhost:11434/v1"
        ).strip().rstrip("/")
        return configured_url[:-3] if configured_url.endswith("/v1") else configured_url

    def is_ollama_server_running(self):
        request = urllib.request.Request(
            f"{self.ollama_api_base()}/api/tags",
            headers={"Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=1.5) as response:
                data = json.loads(response.read().decode("utf-8"))
            return isinstance(data, dict) and isinstance(data.get("models"), list)
        except (
            urllib.error.URLError, TimeoutError, OSError, ValueError,
            TypeError, UnicodeDecodeError
        ):
            return False

    def start_ollama_monitoring(self, interval=5000):
        if not hasattr(self, "ollama_health_timer"):
            self.ollama_health_timer = QTimer(self)
            self.ollama_health_timer.timeout.connect(self.check_ollama_startup)
        self.ollama_health_timer.setInterval(interval)
        if not self.ollama_health_timer.isActive():
            self.ollama_health_timer.start()

    @staticmethod
    def find_ollama_executable():
        executable = shutil.which("ollama")
        if executable:
            return executable

        install_locations = (
            os.path.join(
                os.environ.get("LOCALAPPDATA", ""),
                "Programs", "Ollama", "ollama.exe"
            ),
            os.path.join(
                os.environ.get("ProgramFiles", ""),
                "Ollama", "ollama.exe"
            )
        )
        return next((path for path in install_locations if path and os.path.isfile(path)), None)

    def ensure_ollama_running(self):
        if self.shutting_down:
            return
        if self.is_ollama_server_running():
            self.ollama_start_attempts = 0
            self.start_ollama_monitoring()
            if self.provider_combo.currentData() == "ollama":
                self.status_badge.setText("Ollama ready")
                self.status_badge.setToolTip("Ollama is running on this computer.")
            return

        executable = self.find_ollama_executable()
        if not executable:
            self.start_ollama_monitoring()
            if self.provider_combo.currentData() == "ollama":
                self.status_badge.setText("Ollama not installed")
                self.status_badge.setToolTip(
                    "Nexora could not find ollama.exe. Use Set up offline Ollama to install it."
                )
            return

        if self.ollama_process and self.ollama_process.state() != QProcess.NotRunning:
            return

        self.ollama_start_attempts = 0
        self.ollama_start_error = ""
        process = QProcess(self)
        process.setProgram(executable)
        process.setArguments(["serve"])
        process.setProcessChannelMode(QProcess.MergedChannels)
        process.errorOccurred.connect(self.on_ollama_process_error)
        process.finished.connect(self.on_ollama_process_finished)
        self.ollama_process = process
        if self.provider_combo.currentData() == "ollama":
            self.status_badge.setText("Starting Ollama…")
            self.status_badge.setToolTip("Starting the local Ollama server.")
        process.start()
        self.start_ollama_monitoring(1000)

    def check_ollama_startup(self):
        if self.shutting_down:
            self.ollama_health_timer.stop()
            return
        if self.is_ollama_server_running():
            self.ollama_start_attempts = 0
            self.ollama_health_timer.setInterval(5000)
            if self.provider_combo.currentData() == "ollama":
                self.status_badge.setText("Ollama ready")
                self.status_badge.setToolTip("The local Ollama server is running.")
            return

        if not self.ollama_process or self.ollama_process.state() == QProcess.NotRunning:
            self.ollama_start_attempts = 0
            self.ensure_ollama_running()
            return

        self.ollama_start_attempts += 1
        if self.ollama_start_attempts >= 15:
            self.ollama_health_timer.stop()
            if self.provider_combo.currentData() == "ollama":
                detail = f" {self.ollama_start_error}" if self.ollama_start_error else ""
                self.status_badge.setText("Ollama server unavailable")
                self.status_badge.setToolTip(
                    "Ollama is installed, but its local server did not respond. "
                    "Check Ollama or the server URL in Settings." + detail
                )

    def on_ollama_process_error(self, _error):
        if self.ollama_process:
            self.ollama_start_error = self.ollama_process.errorString()
        if hasattr(self, "ollama_health_timer"):
            self.ollama_health_timer.setInterval(5000)

    def on_ollama_process_finished(self, _exit_code, _exit_status):
        if self.shutting_down:
            return
        if hasattr(self, "ollama_health_timer"):
            self.ollama_health_timer.setInterval(5000)
        if self.provider_combo.currentData() == "ollama" and not self.is_ollama_server_running():
            self.status_badge.setText("Ollama server stopped")
            self.status_badge.setToolTip(
                "The local Ollama server stopped. Restart Nexora or start Ollama from its setup panel."
            )

    def stop_owned_ollama_server(self):
        if not self.ollama_process or self.ollama_process.state() == QProcess.NotRunning:
            return
        self.ollama_process.terminate()
        if not self.ollama_process.waitForFinished(3000):
            self.ollama_process.kill()
            self.ollama_process.waitForFinished(2000)

    def closeEvent(self, event):
        self.shutting_down = True
        if hasattr(self, "ollama_health_timer"):
            self.ollama_health_timer.stop()
        self.stop_owned_ollama_server()
        super().closeEvent(event)

    def copy_conversation(self):
        if not self.current_conversation_id:
            return
        messages = database.get_messages(self.current_conversation_id)
        if not messages:
            self.status_badge.setText("Nothing to copy")
            QTimer.singleShot(1800, lambda: self.status_badge.setText("🟢 Ready"))
            return

        transcript = []
        for message in messages:
            speaker = "You" if message["role"] == "user" else "Nexora"
            entry = f"{speaker}: {message['content']}".rstrip()
            for attachment in message.get("attachments", []):
                entry += f"\n[Image: {attachment['name']}]"
            transcript.append(entry)

        QApplication.clipboard().setText("\n\n".join(transcript))
        self.status_badge.setText("Conversation copied")
        QTimer.singleShot(1800, lambda: self.status_badge.setText("🟢 Ready"))

    def show_first_run_setup(self):
        cfg = load_config()
        if cfg.get("onboarding_completed"):
            return

        dialog = SettingsDialog(self, first_run=True)
        if dialog.exec() != QDialog.Accepted:
            return

        cfg = load_config()
        cfg["onboarding_completed"] = True
        if cfg.get("provider") == "ollama":
            configured_provider = next(
                (
                    provider
                    for provider, spec in PROVIDER_SPECS.items()
                    if provider != "ollama"
                    and cfg.get(spec.get("key_field", ""), "").strip()
                ),
                "gemini"
            )
            cfg["provider"] = configured_provider
            cfg["model"] = PROVIDER_SPECS[configured_provider]["default_model"]
        save_config(cfg)
        provider_index = self.provider_combo.findData(cfg["provider"])
        if provider_index >= 0:
            self.provider_combo.setCurrentIndex(provider_index)
        self.on_provider_changed()

        prompt = QMessageBox(self)
        prompt.setWindowTitle("Set up offline chat?")
        prompt.setIcon(QMessageBox.Information)
        prompt.setText("Would you like to download Ollama for offline chat?")
        prompt.setInformativeText(
            "Ollama is optional and installs separately. After installing it, Nexora can help you check "
            "the connection and download a local AI model. You can skip this and set it up later."
        )
        download_button = prompt.addButton("Download Ollama", QMessageBox.AcceptRole)
        prompt.addButton("Skip for later", QMessageBox.RejectRole)
        prompt.exec()
        if prompt.clickedButton() == download_button:
            self.open_ollama_setup()

    def open_ollama_setup(self):
        dialog = OllamaSetupDialog(self)
        if dialog.exec() == QDialog.Accepted:
            model = load_config().get("ollama_model", "llama3.2")
            provider_index = self.provider_combo.findData("ollama")
            if provider_index >= 0:
                self.provider_combo.setCurrentIndex(provider_index)
            self.model_combo.setCurrentText(model)
            self.status_badge.setText(f"Offline ready: {model}")
            self.status_badge.setToolTip("Ollama is running and this model is installed for local chat.")

    def on_provider_changed(self):
        provider_key = self.provider_combo.currentData()
        spec = PROVIDER_SPECS.get(provider_key, {})
        cfg = load_config()
        preferred_model = cfg.get("model") if cfg.get("provider") == provider_key else None
        self.model_combo.clear()
        for m in spec.get("models", []):
            self.model_combo.addItem(m)
        if preferred_model and self.model_combo.findText(preferred_model) >= 0:
            self.model_combo.setCurrentText(preferred_model)
        elif spec.get("default_model"):
            self.model_combo.setCurrentText(spec["default_model"])

        if provider_key == "ollama":
            status = "Ollama required"
            self.status_badge.setToolTip(
                "Local chat requires a separately installed Ollama server and a downloaded model."
            )
        elif not cfg.get(spec.get("key_field", ""), "").strip():
            status = "API key needed"
            self.status_badge.setToolTip(
                "Add your own provider API key in Settings to use online chat."
            )
        else:
            status = f"Ready: {spec.get('name', 'AI')}"
            self.status_badge.setToolTip("")
        self.status_badge.setText(status)

        cfg["provider"] = provider_key
        cfg["model"] = self.model_combo.currentText()
        save_config(cfg)

    def on_model_changed(self):
        model = self.model_combo.currentText()
        cfg = load_config()
        cfg["provider"] = self.provider_combo.currentData()
        cfg["model"] = model
        save_config(cfg)
        if self.current_conversation_id and model:
            provider = self.provider_combo.currentData()
            database.update_conversation_model(self.current_conversation_id, provider, model)

    def load_conversations_list(self, selected_conversation_id=None):
        self.history_list.clear()
        convs = database.list_conversations()
        if not convs:
            self.start_new_chat()
            return

        for c in convs:
            prefix = "📌  " if c.get("pinned") else ""
            item = QListWidgetItem(f"{prefix}{c['title']}")
            item.setData(Qt.UserRole, c["id"])
            item.setData(Qt.UserRole + 1, c["title"])
            item.setData(Qt.UserRole + 2, bool(c.get("pinned")))
            self.history_list.addItem(item)

        selected = next(
            (c for c in convs if c["id"] == selected_conversation_id),
            convs[0]
        )
        row = next(
            index for index, conversation in enumerate(convs)
            if conversation["id"] == selected["id"]
        )
        self.history_list.setCurrentRow(row)
        self.load_conversation(selected["id"], selected["title"])

    def start_new_chat(self):
        provider = self.provider_combo.currentData()
        model = self.model_combo.currentText()
        conv_id = database.create_conversation("New Chat", provider, model)
        self.load_conversations_list(conv_id)

    def on_conversation_selected(self, item: QListWidgetItem):
        conv_id = item.data(Qt.UserRole)
        title = item.data(Qt.UserRole + 1) or item.text()
        self.load_conversation(conv_id, title)

    def show_conversation_context_menu(self, position):
        item = self.history_list.itemAt(position)
        if item is None:
            return

        self.history_list.setCurrentItem(item)
        conversation_id = item.data(Qt.UserRole)
        title = item.data(Qt.UserRole + 1) or item.text()
        is_pinned = bool(item.data(Qt.UserRole + 2))

        menu = QMenu(self)
        rename_action = menu.addAction("Rename chat")
        pin_action = menu.addAction("Unpin chat" if is_pinned else "Pin chat")
        menu.addSeparator()
        delete_action = menu.addAction("Delete chat")
        selected_action = menu.exec(self.history_list.mapToGlobal(position))
        active_conversation_id = self.current_conversation_id

        if selected_action == rename_action:
            self.rename_conversation(
                conversation_id, title, active_conversation_id
            )
        elif selected_action == pin_action:
            database.set_conversation_pinned(conversation_id, not is_pinned)
            self.load_conversations_list(active_conversation_id)
        elif selected_action == delete_action:
            self.delete_conversation_by_id(conversation_id)

    def rename_conversation(
        self,
        conversation_id,
        current_title,
        active_conversation_id=None
    ):
        title, accepted = QInputDialog.getText(
            self, "Rename chat", "Chat title:", text=current_title
        )
        title = title.strip()
        if not accepted or not title or title == current_title:
            return

        database.rename_conversation(conversation_id, title)
        self.load_conversations_list(active_conversation_id or conversation_id)

    def load_conversation(self, conv_id: str, title: str):
        self.current_conversation_id = conv_id
        self.chat_title_lbl.setText(title)
        self.clear_chat_display()

        messages = database.get_messages(conv_id)
        for m in messages:
            card = MessageCard(
                m["role"], m["content"], m.get("attachments"), m.get("timestamp", "")
            )
            # Insert before the stretch at the end
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, card)

        self.scroll_to_bottom()

    def clear_chat_display(self):
        # Remove all message cards except the stretch item
        while self.messages_layout.count() > 1:
            child = self.messages_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def delete_current_conversation(self):
        if not self.current_conversation_id:
            return
        self.delete_conversation_by_id(self.current_conversation_id)

    def delete_conversation_by_id(self, conversation_id):
        ans = QMessageBox.question(
            self,
            "Delete Conversation",
            "Are you sure you want to delete this chat?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ans == QMessageBox.Yes:
            database.delete_conversation(conversation_id)
            remaining = [
                self.history_list.item(index).data(Qt.UserRole)
                for index in range(self.history_list.count())
                if self.history_list.item(index).data(Qt.UserRole) != conversation_id
            ]
            if conversation_id == self.current_conversation_id:
                self.current_conversation_id = None
            selected_id = (
                self.current_conversation_id
                if self.current_conversation_id in remaining else
                (remaining[0] if remaining else None)
            )
            self.load_conversations_list(selected_id)

    def add_images(self):
        remaining = MAX_ATTACHMENTS - len(self.pending_images)
        if remaining <= 0:
            QMessageBox.information(
                self, "Image limit reached",
                f"You can attach up to {MAX_ATTACHMENTS} images to one message."
            )
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Attach images",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"
        )
        for path in paths:
            if path not in self.pending_images and len(self.pending_images) < MAX_ATTACHMENTS:
                self.pending_images.append(path)
        self.refresh_draft_images()

    def remove_draft_image(self, path):
        if path in self.pending_images:
            self.pending_images.remove(path)
            self.refresh_draft_images()

    def refresh_draft_images(self):
        while self.draft_images_layout.count():
            item = self.draft_images_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for path in self.pending_images:
            image_card = QFrame()
            image_card.setStyleSheet(
                "QFrame { background: #202023; border: 1px solid #3f3f46; border-radius: 8px; }"
            )
            card_layout = QVBoxLayout(image_card)
            card_layout.setContentsMargins(6, 6, 6, 6)
            card_layout.setSpacing(3)

            image_label = QLabel()
            reader = QImageReader(path)
            source_size = reader.size()
            if source_size.isValid():
                reader.setScaledSize(source_size.scaled(112, 76, Qt.KeepAspectRatio))
            image = reader.read()
            if not image.isNull():
                image_label.setPixmap(QPixmap.fromImage(image))
            else:
                image_label.setText("Preview unavailable")
            image_label.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(image_label)

            name = QLabel(os.path.basename(path))
            name.setMaximumWidth(112)
            name.setStyleSheet("color: #d4d4d8; font-size: 10px; border: none;")
            name.setToolTip(path)
            card_layout.addWidget(name)

            remove_button = QPushButton("Remove")
            remove_button.setStyleSheet(
                "QPushButton { background: transparent; color: #fca5a5; border: none; font-size: 10px; }"
            )
            remove_button.clicked.connect(lambda _checked=False, image_path=path: self.remove_draft_image(image_path))
            card_layout.addWidget(remove_button)
            self.draft_images_layout.addWidget(image_card)

        self.draft_images_widget.setVisible(bool(self.pending_images))
        self.attachment_notice.setVisible(bool(self.pending_images))

    def send_message(self):
        text = self.chat_input.toPlainText().strip()
        if not text and not self.pending_images:
            return

        provider = self.provider_combo.currentData()
        model = self.model_combo.currentText().strip()
        spec = PROVIDER_SPECS.get(provider, {})
        if not model:
            QMessageBox.warning(
                self,
                "Choose a model",
                "Select a model in the chat composer before sending a message."
            )
            return

        if self.pending_images and not model_supports_vision(provider, model):
            prompt = QMessageBox(self)
            prompt.setWindowTitle("This model may not support images")
            prompt.setIcon(QMessageBox.Warning)
            prompt.setText(f"{model} may not be able to understand image attachments.")
            prompt.setInformativeText(
                "Choose a vision-capable model such as Gemini, Pixtral, or an Ollama vision model, "
                "or send anyway and the model may ignore the images."
            )
            switch_button = prompt.addButton("Choose model", QMessageBox.AcceptRole)
            send_button = prompt.addButton("Send anyway", QMessageBox.DestructiveRole)
            prompt.addButton("Cancel", QMessageBox.RejectRole)
            prompt.exec()
            if prompt.clickedButton() == switch_button:
                self.model_combo.showPopup()
                return
            if prompt.clickedButton() != send_button:
                return

        if provider != "ollama":
            cfg = load_config()
            key_name = spec.get("key_field")
            if key_name and not cfg.get(key_name, "").strip():
                message = QMessageBox(self)
                message.setWindowTitle("API key required")
                message.setIcon(QMessageBox.Information)
                message.setText(f"{spec.get('name', 'This provider')} requires an API key.")
                key_urls = {
                    "groq": "https://console.groq.com/keys",
                    "gemini": "https://aistudio.google.com/app/apikey",
                    "openrouter": "https://openrouter.ai/keys",
                    "cerebras": "https://cloud.cerebras.ai/",
                    "mistral": "https://console.mistral.ai/"
                }
                key_url = key_urls.get(provider)
                key_link = f'<a href="{key_url}">Open {spec.get("name", "provider")} key setup</a><br><br>' if key_url else ""
                message.setInformativeText(
                    f"{key_link}Nexora cannot connect to an online AI provider until you add your own API key. "
                    "Enter it in Settings. Provider account limits or charges may apply; never paste your key into the chat."
                )
                settings_button = message.addButton("Open Settings", QMessageBox.AcceptRole)
                message.addButton(QMessageBox.Cancel)
                message.exec()
                if message.clickedButton() == settings_button:
                    self.open_settings()
                return

        if self.pending_images:
            saved_attachments = []
            try:
                for image_path in self.pending_images:
                    saved_attachments.append(save_image_attachment(image_path))
            except (OSError, ValueError) as ex:
                for attachment in saved_attachments:
                    try:
                        os.remove(attachment["file_path"])
                    except FileNotFoundError:
                        pass
                QMessageBox.warning(self, "Could not attach image", str(ex))
                return
            if not text:
                text = "Please describe this image."
        else:
            saved_attachments = []

        if not self.current_conversation_id:
            self.start_new_chat()

        self.chat_input.clear()
        self.pending_images.clear()
        self.refresh_draft_images()

        # 1. Add user card to UI
        # 2. Save user message to database
        database.add_message(
            self.current_conversation_id, "user", text, saved_attachments
        )
        user_card = MessageCard(
            "user", text, saved_attachments, datetime.now().isoformat()
        )
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, user_card)

        # 3. Create placeholder assistant card
        self.accumulated_response = ""
        self.current_assistant_card = MessageCard("assistant", "Thinking...")
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, self.current_assistant_card)
        self.scroll_to_bottom()

        # Update UI controls
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.send_btn.hide()
        self.stop_btn.show()
        self.status_badge.setText("⚡ Generating...")

        # 4. Prepare message history for API
        db_messages = database.get_messages(self.current_conversation_id)

        # 5. Start background worker thread
        self.worker = LLMWorker(provider, model, db_messages, parent=self)
        self.worker.chunk_ready.connect(self.on_chunk_received)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.error_occurred.connect(self.on_worker_error)
        self.worker.start()

    def on_chunk_received(self, chunk: str):
        if not self.accumulated_response:
            self.accumulated_response = chunk
        else:
            self.accumulated_response += chunk

        if self.current_assistant_card:
            self.current_assistant_card.set_content(self.accumulated_response)
        self.scroll_to_bottom()

    def on_generation_finished(self, full_response: str):
        if self.current_assistant_card:
            self.current_assistant_card.set_content(full_response if full_response else self.accumulated_response)
            self.current_assistant_card.set_timestamp(datetime.now().isoformat())

        # Save assistant message to DB
        if self.current_conversation_id and (full_response or self.accumulated_response):
            database.add_message(self.current_conversation_id, "assistant", full_response or self.accumulated_response)

        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stop_btn.hide()
        self.send_btn.show()
        self.status_badge.setText("🟢 Ready")
        self.scroll_to_bottom()

        # Refresh conversation title in sidebar if updated
        convs = database.list_conversations()
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            c_id = item.data(Qt.UserRole)
            for c in convs:
                if c["id"] == c_id:
                    prefix = "📌  " if c.get("pinned") else ""
                    item.setText(f"{prefix}{c['title']}")
                    item.setData(Qt.UserRole + 1, c["title"])
                    item.setData(Qt.UserRole + 2, bool(c.get("pinned")))
                    if c_id == self.current_conversation_id:
                        self.chat_title_lbl.setText(c["title"])
                    break

    def on_worker_error(self, err_msg: str):
        if self.current_assistant_card:
            self.current_assistant_card.set_content(f"**Error:**\n{err_msg}")
            self.current_assistant_card.set_timestamp(datetime.now().isoformat())

        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stop_btn.hide()
        self.send_btn.show()
        self.status_badge.setText("🔴 Error")
        if (
            self.worker
            and self.worker.provider == "ollama"
            and "Could not connect to the local Ollama server" in err_msg
        ):
            self.ensure_ollama_running()
        self.scroll_to_bottom()

    def stop_generation(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_badge.setText("⏹ Stopped")

    def scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

# ------------------------------------------------------------------------------
# Application Entry Point
# ------------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Nexora")
    app.setWindowIcon(QIcon(APP_ICON_PATH))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
