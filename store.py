"""SQLite-backed persistent storage for chat settings, warnings, and notes."""
from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_settings (
    chat_id INTEGER PRIMARY KEY,
    welcome_text TEXT,
    goodbye_text TEXT,
    rules_text TEXT,
    antiflood_enabled INTEGER NOT NULL DEFAULT 0,
    antiflood_limit INTEGER NOT NULL DEFAULT 6,
    antiflood_window INTEGER NOT NULL DEFAULT 8,
    block_links INTEGER NOT NULL DEFAULT 0,
    block_forwards INTEGER NOT NULL DEFAULT 0,
    warn_limit INTEGER NOT NULL DEFAULT 3
);

CREATE TABLE IF NOT EXISTS warnings (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE IF NOT EXISTS notes (
    chat_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (chat_id, name)
);
"""


class Store:
    """Thin synchronous SQLite wrapper exposed via asyncio.to_thread."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = asyncio.Lock()
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    async def _run(self, fn, *args, **kwargs):
        async with self._lock:
            return await asyncio.to_thread(fn, *args, **kwargs)

    # ----- chat settings -----
    def _get_settings_sync(self, chat_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            if row is None:
                conn.execute("INSERT INTO chat_settings (chat_id) VALUES (?)", (chat_id,))
                row = conn.execute(
                    "SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,)
                ).fetchone()
            return dict(row)

    async def get_settings(self, chat_id: int) -> dict[str, Any]:
        return await self._run(self._get_settings_sync, chat_id)

    def _update_setting_sync(self, chat_id: int, key: str, value: Any) -> None:
        allowed = {
            "welcome_text",
            "goodbye_text",
            "rules_text",
            "antiflood_enabled",
            "antiflood_limit",
            "antiflood_window",
            "block_links",
            "block_forwards",
            "warn_limit",
        }
        if key not in allowed:
            raise ValueError(f"Unknown setting: {key}")
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO chat_settings (chat_id) VALUES (?)", (chat_id,)
            )
            conn.execute(
                f"UPDATE chat_settings SET {key} = ? WHERE chat_id = ?",
                (value, chat_id),
            )

    async def update_setting(self, chat_id: int, key: str, value: Any) -> None:
        await self._run(self._update_setting_sync, chat_id, key, value)

    # ----- warnings -----
    def _add_warning_sync(self, chat_id: int, user_id: int) -> int:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO warnings (chat_id, user_id, count) VALUES (?, ?, 1)
                   ON CONFLICT(chat_id, user_id) DO UPDATE SET count = count + 1""",
                (chat_id, user_id),
            )
            row = conn.execute(
                "SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id),
            ).fetchone()
            return int(row["count"])

    async def add_warning(self, chat_id: int, user_id: int) -> int:
        return await self._run(self._add_warning_sync, chat_id, user_id)

    def _get_warnings_sync(self, chat_id: int, user_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id),
            ).fetchone()
            return int(row["count"]) if row else 0

    async def get_warnings(self, chat_id: int, user_id: int) -> int:
        return await self._run(self._get_warnings_sync, chat_id, user_id)

    def _reset_warnings_sync(self, chat_id: int, user_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM warnings WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id),
            )

    async def reset_warnings(self, chat_id: int, user_id: int) -> None:
        await self._run(self._reset_warnings_sync, chat_id, user_id)

    # ----- notes -----
    def _save_note_sync(self, chat_id: int, name: str, content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO notes (chat_id, name, content) VALUES (?, ?, ?)
                   ON CONFLICT(chat_id, name) DO UPDATE SET content = excluded.content""",
                (chat_id, name.lower(), content),
            )

    async def save_note(self, chat_id: int, name: str, content: str) -> None:
        await self._run(self._save_note_sync, chat_id, name, content)

    def _get_note_sync(self, chat_id: int, name: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT content FROM notes WHERE chat_id = ? AND name = ?",
                (chat_id, name.lower()),
            ).fetchone()
            return row["content"] if row else None

    async def get_note(self, chat_id: int, name: str) -> str | None:
        return await self._run(self._get_note_sync, chat_id, name)

    def _list_notes_sync(self, chat_id: int) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name FROM notes WHERE chat_id = ? ORDER BY name", (chat_id,)
            ).fetchall()
            return [r["name"] for r in rows]

    async def list_notes(self, chat_id: int) -> list[str]:
        return await self._run(self._list_notes_sync, chat_id)

    def _delete_note_sync(self, chat_id: int, name: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM notes WHERE chat_id = ? AND name = ?",
                (chat_id, name.lower()),
            )
            return cur.rowcount > 0

    async def delete_note(self, chat_id: int, name: str) -> bool:
        return await self._run(self._delete_note_sync, chat_id, name)
