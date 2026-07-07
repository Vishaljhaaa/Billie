from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.schemas import SourceStatus


class SourceStateStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_state (
                    source_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def get_fingerprint(self, source_id: str) -> str | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT fingerprint FROM source_state WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        return row[0] if row else None

    def list_sources(self) -> list[SourceStatus]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT source_id, fingerprint, updated_at FROM source_state ORDER BY source_id"
            ).fetchall()
        return [
            SourceStatus(source_id=source_id, fingerprint=fingerprint, updated_at=updated_at)
            for source_id, fingerprint, updated_at in rows
        ]

    def upsert_fingerprint(self, source_id: str, fingerprint: str, updated_at: str) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO source_state (source_id, fingerprint, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    fingerprint = excluded.fingerprint,
                    updated_at = excluded.updated_at
                """,
                (source_id, fingerprint, updated_at),
            )
