from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Ensure the project root is on sys.path so this script can be run directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import build_services
from app.config import AppConfig, AuthConfig, LLMConfig


class InMemoryVectorStore:
    def __init__(self) -> None:
        self.documents: dict[str, tuple[list[str], str]] = {}

    def replace_source_chunks(self, source_id: str, chunks: list[str], location: str) -> None:
        self.documents[source_id] = (chunks, location)

    def search(self, query: str, top_k: int):
        results = []
        for chunks, location in self.documents.values():
            for chunk in chunks[:top_k]:
                results.append({"content": chunk, "metadata": {"location": location}})
        return results[:top_k]


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        knowledge = root / "knowledge.txt"
        knowledge.write_text("The chatbot updates its vector database on a schedule and also supports manual sync.", encoding="utf-8")

        config = AppConfig(
            poll_interval_minutes=60,
            chunk_size=120,
            chunk_overlap=10,
            top_k=3,
            memory_window=4,
            vector_store_dir=root / "chroma",
            metadata_db_path=root / "state.db",
            session_store_path=root / "sessions.json",
            source_timeout_seconds=5,
            source_max_retries=2,
            source_retry_backoff_seconds=0.0,
            llm=LLMConfig(api_key=None, model="unused", base_url="http://unused", timeout_seconds=5, max_retries=1),
            auth=AuthConfig(api_key=None, admin_key=None),
            sources=[],
        )

        vector_store = InMemoryVectorStore()
        vector_store.replace_source_chunks("local-doc", [knowledge.read_text(encoding="utf-8")], str(knowledge))

        services = build_services(config, vector_store=vector_store)
        chatbot = services.chatbot

        response = chatbot.answer("How does it update?", session_id="demo-session")
        print(json.dumps(json.loads(response.json()), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
