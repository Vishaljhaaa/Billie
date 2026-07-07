from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import AppConfig, AuthConfig, LLMConfig, SourceConfig
from app.main import build_services, create_app


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


def make_config(tmp_path: Path) -> AppConfig:
    knowledge_file = tmp_path / "knowledge.txt"
    knowledge_file.write_text(
        "The chatbot updates its vector database on a schedule and also supports manual sync.",
        encoding="utf-8",
    )
    return AppConfig(
        poll_interval_minutes=60,
        chunk_size=120,
        chunk_overlap=10,
        top_k=2,
        vector_store_dir=tmp_path / "chroma",
        metadata_db_path=tmp_path / "state.db",
        source_timeout_seconds=5,
        source_max_retries=2,
        source_retry_backoff_seconds=0.0,
        llm=LLMConfig(api_key=None, model="unused", base_url="http://unused", timeout_seconds=5, max_retries=1),
        auth=AuthConfig(api_key="chat-secret", admin_key="admin-secret"),
        sources=[SourceConfig(id="local-doc", type="file", path=str(knowledge_file))],
    )


def test_api_auth_and_admin_status(tmp_path: Path):
    config = make_config(tmp_path)
    services = build_services(config, vector_store=InMemoryVectorStore())
    app = create_app(config, services=services, run_scheduler=False)

    with TestClient(app) as client:
        admin_unauthorized = client.get("/admin/status")
        assert admin_unauthorized.status_code == 401

        admin_status = client.get("/admin/status", headers={"X-Admin-Key": "admin-secret"})
        assert admin_status.status_code == 200
        assert admin_status.json()["source_count"] == 1

        chat_unauthorized = client.post("/chat", json={"question": "How does the chatbot update?"})
        assert chat_unauthorized.status_code == 401

        chat_response = client.post(
            "/chat",
            json={"question": "How does the chatbot update?"},
            headers={"X-API-Key": "chat-secret"},
        )
        assert chat_response.status_code == 200
        body = chat_response.json()
        assert body["sources"]
        assert body["used_llm"] is False
