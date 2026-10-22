"""
database.py
===========
SQLite persistence layer for conversations and messages.
"""

import sqlite3
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

APP_DATA_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "Nexora"
)
ATTACHMENTS_DIR = os.path.join(APP_DATA_DIR, "attachments")
LEGACY_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history.db")

def get_db_path() -> str:
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    db_path = os.path.join(APP_DATA_DIR, "chat_history.db")
    if not os.path.exists(db_path) and os.path.exists(LEGACY_DB_PATH):
        source = sqlite3.connect(LEGACY_DB_PATH)
        destination = sqlite3.connect(db_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
    return db_path

def init_db():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            pinned INTEGER NOT NULL DEFAULT 0
        )
    """)
    cursor.execute("PRAGMA table_info(conversations)")
    conversation_columns = {row[1] for row in cursor.fetchall()}
    if "pinned" not in conversation_columns:
        cursor.execute(
            "ALTER TABLE conversations ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0"
        )
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def create_conversation(
    title: str = "New Chat",
    provider: str = "ollama",
    model: str = "llama3.2"
) -> str:
    conv_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (id, title, created_at, provider, model) VALUES (?, ?, ?, ?, ?)",
        (conv_id, title, now, provider, model)
    )
    conn.commit()
    conn.close()
    return conv_id

def list_conversations() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM conversations ORDER BY pinned DESC, created_at DESC"
    )
    rows = cursor.fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result

def get_messages(conversation_id: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,)
    )
    rows = cursor.fetchall()
    result = []
    for row in rows:
        message = dict(row)
        cursor.execute(
            "SELECT name, file_path, mime_type FROM message_attachments WHERE message_id = ? ORDER BY id ASC",
            (message["id"],)
        )
        message["attachments"] = [dict(attachment) for attachment in cursor.fetchall()]
        result.append(message)
    conn.close()
    return result

def add_message(
    conversation_id: str,
    role: str,
    content: str,
    attachments: Optional[List[Dict[str, str]]] = None
) -> int:
    now = datetime.now().isoformat()
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, now)
    )
    message_id = cursor.lastrowid
    for attachment in attachments or []:
        cursor.execute(
            "INSERT INTO message_attachments (message_id, name, file_path, mime_type) VALUES (?, ?, ?, ?)",
            (message_id, attachment["name"], attachment["file_path"], attachment["mime_type"])
        )
    
    # Auto-update conversation title if it's the first user message and default title
    if role == "user":
        cursor.execute("SELECT title FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        if row and (row[0] == "New Chat" or not row[0]):
            preview_title = content.strip().split("\n")[0][:35]
            if len(content.strip().split("\n")[0]) > 35:
                preview_title += "..."
            cursor.execute("UPDATE conversations SET title = ? WHERE id = ?", (preview_title, conversation_id))
            
    conn.commit()
    conn.close()
    return message_id

def delete_conversation(conversation_id: str) -> None:
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ma.file_path
        FROM message_attachments ma
        JOIN messages m ON ma.message_id = m.id
        WHERE m.conversation_id = ?
    """, (conversation_id,))
    attachment_paths = [row[0] for row in cursor.fetchall()]
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()
    for path in attachment_paths:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

def rename_conversation(conversation_id: str, title: str) -> None:
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE conversations SET title = ? WHERE id = ?",
        (title, conversation_id)
    )
    conn.commit()
    conn.close()

def set_conversation_pinned(conversation_id: str, pinned: bool) -> None:
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE conversations SET pinned = ? WHERE id = ?",
        (int(pinned), conversation_id)
    )
    conn.commit()
    conn.close()

def update_conversation_model(conversation_id: str, provider: str, model: str) -> None:
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("UPDATE conversations SET provider = ?, model = ? WHERE id = ?", (provider, model, conversation_id))
    conn.commit()
    conn.close()

# Initialize DB on load
init_db()
