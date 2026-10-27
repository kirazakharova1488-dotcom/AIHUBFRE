"""Storage repositories for conversations, agents, extensions and usage."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from ai_hub.storage.database import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn = connection

    def create(self, title: str | None = None) -> int:
        now = _now()
        cursor = self.conn.execute(
            "INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)",
            (title, now, now),
        )
        self.conn.commit()
        return cursor.lastrowid

    def add_message(self, conversation_id: int, role: str, content: str, model: str | None = None,
                    tokens_in: int = 0, tokens_out: int = 0) -> int:
        cursor = self.conn.execute(
            "INSERT INTO messages (conversation_id, role, content, model, tokens_in, tokens_out, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (conversation_id, role, content, model, tokens_in, tokens_out, _now()),
        )
        self.conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (_now(), conversation_id),
        )
        self.conn.commit()
        return cursor.lastrowid

    def history(self, conversation_id: int, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT role, content, model, tokens_in, tokens_out, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY id ASC LIMIT ?",
            (conversation_id, limit),
        )
        return [dict(row) for row in rows]

    def list_conversations(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in rows]


class AgentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn = connection

    def create(self, agent_id: str, name: str, description: str | None, system_prompt: str | None,
               model: str | None, permissions: str | None, token_limit: int | None, max_steps: int) -> None:
        now = _now()
        self.conn.execute(
            "INSERT INTO agents (id, name, description, system_prompt, model, permissions, token_limit, "
            "max_steps, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (agent_id, name, description, system_prompt, model, permissions, token_limit, max_steps, now, now),
        )
        self.conn.commit()

    def get(self, agent_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
        return dict(row) if row else None

    def by_name(self, name: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None

    def list(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM agents ORDER BY updated_at DESC")
        return [dict(row) for row in rows]

    def delete(self, agent_id: str) -> bool:
        cursor = self.conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        self.conn.commit()
        return cursor.rowcount > 0


class ExtensionRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn = connection

    def create(self, ext_id: str, name: str, type_: str, manifest_path: str | None,
               version: str, enabled: int, source: str | None) -> None:
        now = _now()
        self.conn.execute(
            "INSERT INTO extensions (id, name, type, manifest_path, version, enabled, source, created_at, "
            "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ext_id, name, type_, manifest_path, version, enabled, source, now, now),
        )
        self.conn.commit()

    def get(self, ext_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM extensions WHERE id = ?", (ext_id,)).fetchone()
        return dict(row) if row else None

    def list(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM extensions ORDER BY updated_at DESC")
        return [dict(row) for row in rows]

    def set_enabled(self, ext_id: str, enabled: bool) -> bool:
        cursor = self.conn.execute(
            "UPDATE extensions SET enabled = ?, updated_at = ? WHERE id = ?",
            (1 if enabled else 0, _now(), ext_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def delete(self, ext_id: str) -> bool:
        cursor = self.conn.execute("DELETE FROM extensions WHERE id = ?", (ext_id,))
        self.conn.commit()
        return cursor.rowcount > 0


class UsageRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn = connection

    def record(self, model: str, tokens_in: int, tokens_out: int) -> None:
        self.conn.execute(
            "INSERT INTO usage_stats (model, tokens_in, tokens_out, recorded_at) VALUES (?, ?, ?, ?)",
            (model, tokens_in, tokens_out, _now()),
        )
        self.conn.commit()

    def totals(self) -> dict:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(tokens_in), 0) AS in_tok, COALESCE(SUM(tokens_out), 0) AS out_tok FROM usage_stats"
        ).fetchone()
        return {"in": int(row["in_tok"]), "out": int(row["out_tok"])}
