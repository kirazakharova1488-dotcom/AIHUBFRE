"""SQLite database connection and migration runner."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ai_hub.config import get_db_path
from ai_hub.storage.migrations import MIGRATIONS


def get_connection(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def migrate(connection: sqlite3.Connection | None = None) -> None:
    own = connection is None
    connection = connection or get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
        )
        applied = {row["version"] for row in cursor.execute("SELECT version FROM schema_migrations")}
        for index, migration in enumerate(MIGRATIONS, start=1):
            if index in applied:
                continue
            cursor.executescript(migration)
            cursor.execute("INSERT INTO schema_migrations (version) VALUES (?)", (index,))
        connection.commit()
    finally:
        if own:
            connection.close()
