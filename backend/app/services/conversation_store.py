"""SQLite-backed state for multi-turn packaging conversations."""

import json
from typing import Any, Dict

from app.db import get_db_connection


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
        row = conn.execute(
            "SELECT state_json FROM chatbot_conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        return json.loads(row["state_json"]) if row else None
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
