from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


class ConversationMemoryStore:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._sessions = self._load()

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        if not self.storage_path.exists():
            return {}
        return json.loads(self.storage_path.read_text(encoding="utf-8"))

    def _persist(self) -> None:
        self.storage_path.write_text(json.dumps(self._sessions, indent=2), encoding="utf-8")

    def recent_turns(self, session_id: str, limit: int) -> list[dict[str, Any]]:
        with self._lock:
            turns = self._sessions.get(session_id, [])
            return [dict(turn) for turn in turns[-limit:]]

    def append_turn(
        self,
        session_id: str,
        *,
        question: str,
        answer: str,
        sources: list[str],
        visual_summaries: list[str],
    ) -> None:
        with self._lock:
            session = self._sessions.setdefault(session_id, [])
            session.append(
                {
                    "question": question,
                    "answer": answer,
                    "sources": sources,
                    "visual_summaries": visual_summaries,
                }
            )
            self._persist()
