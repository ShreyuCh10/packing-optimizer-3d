"""SQLite-backed state for multi-turn packaging conversations."""

import json
import logging
import os
from typing import Any, Dict

from app.db import get_db_connection

logger = logging.getLogger(__name__)
CONVERSATION_TTL_DAYS = max(1, int(os.getenv("CHAT_CONVERSATION_TTL_DAYS", "30")))


def load_conversation(conversation_id: str) -> Dict[str, Any] | None:
    conn = get_db_connection()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS chatbot_conversations (
                conversation_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.execute(
            "DELETE FROM chatbot_conversations WHERE updated_at < datetime('now', ?)",
            (f"-{CONVERSATION_TTL_DAYS} days",),
        )
        conn.commit()
        row = conn.execute(
            "SELECT state_json FROM chatbot_conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        if not row:
            return None
        try:
            state = json.loads(row["state_json"])
            return state if isinstance(state, dict) else None
        except (TypeError, json.JSONDecodeError):
            logger.exception("conversation.state.invalid conversation_id=%s", conversation_id)
            conn.execute("DELETE FROM chatbot_conversations WHERE conversation_id = ?", (conversation_id,))
            conn.commit()
            return None
    finally:
        conn.close()


def save_conversation(conversation_id: str, state: Dict[str, Any]) -> None:
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS chatbot_conversations (
                    conversation_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            conn.execute(
                """INSERT INTO chatbot_conversations (conversation_id, state_json, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(conversation_id) DO UPDATE SET
                     state_json = excluded.state_json,
                     updated_at = CURRENT_TIMESTAMP""",
                (conversation_id, json.dumps(state, ensure_ascii=False)),
            )
    finally:
        conn.close()
