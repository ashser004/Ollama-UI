# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
database.py — SQLite helper for chat history storage.

All data stored in AIUI/chats.db — fully portable.
"""

import sqlite3
import os
import json
from datetime import datetime
from app import config


def _get_connection() -> sqlite3.Connection:
    """Get a connection to the chat database."""
    db_path = config.get_db_path()
    if not db_path:
        raise RuntimeError("AIUI directory not configured")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT 'New Chat',
                model TEXT NOT NULL,
                is_agentic INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                model TEXT,
                images TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv
                ON messages(conversation_id);
        """)
        conn.commit()
    finally:
        conn.close()


# ─── Conversations ────────────────────────────────────────────

def create_conversation(model: str, title: str = "New Chat", is_agentic: bool = False) -> int:
    """Create a new conversation and return its ID."""
    now = datetime.now().isoformat()
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO conversations (title, model, is_agentic, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (title, model, int(is_agentic), now, now)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_conversations() -> list[dict]:
    """Get all conversations, newest first."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def search_conversations(query: str = "", model: str | None = None) -> list[dict]:
    """Search conversations by title, model, or message content."""
    conn = _get_connection()
    try:
        sql = """
            SELECT DISTINCT c.*
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            WHERE 1=1
        """
        params: list[str] = []

        if query:
            like = f"%{query.lower()}%"
            sql += """
                AND (
                    LOWER(c.title) LIKE ?
                    OR LOWER(c.model) LIKE ?
                    OR LOWER(COALESCE(m.content, '')) LIKE ?
                )
            """
            params.extend([like, like, like])

        if model and model.lower() != "all models":
            sql += " AND c.model = ?"
            params.append(model)

        sql += " ORDER BY c.updated_at DESC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_conversation(conv_id: int) -> dict | None:
    """Get a single conversation by ID."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_conversation_title(conv_id: int, title: str):
    """Update conversation title."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, datetime.now().isoformat(), conv_id)
        )
        conn.commit()
    finally:
        conn.close()


def update_conversation_model(conv_id: int, model: str):
    """Update conversation's active model when user switches models mid-chat."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE conversations SET model = ?, updated_at = ? WHERE id = ?",
            (model, datetime.now().isoformat(), conv_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_conversation(conv_id: int):
    """Delete a conversation and all its messages."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.commit()
    finally:
        conn.close()


# ─── Messages ─────────────────────────────────────────────────

def add_message(conv_id: int, role: str, content: str,
                model: str = None, images: list[str] = None) -> int:
    """Add a message to a conversation. Returns message ID."""
    now = datetime.now().isoformat()
    images_json = json.dumps(images) if images else None
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, model, images, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (conv_id, role, content, model, images_json, now)
        )
        # Update conversation's updated_at
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conv_id)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_messages(conv_id: int) -> list[dict]:
    """Get all messages for a conversation, in order."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conv_id,)
        ).fetchall()
        messages = []
        for row in rows:
            msg = dict(row)
            if msg.get("images"):
                msg["images"] = json.loads(msg["images"])
            messages.append(msg)
        return messages
    finally:
        conn.close()


def get_recent_messages(conv_id: int, limit: int = 20) -> list[dict]:
    """Get the most recent N messages for context management."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conv_id, limit)
        ).fetchall()
        messages = []
        for row in reversed(rows):  # reverse to chronological order
            msg = dict(row)
            if msg.get("images"):
                msg["images"] = json.loads(msg["images"])
            messages.append(msg)
        return messages
    finally:
        conn.close()


def delete_message(msg_id: int):
    """Delete a single message."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        conn.commit()
    finally:
        conn.close()
