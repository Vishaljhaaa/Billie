from __future__ import annotations

from pathlib import Path

from app.chatbot import RetrievalChatbot
from app.config import AppConfig, AuthConfig, LLMConfig
from app.monitoring import AppMonitor


class FakeVectorStore:
    def search(self, query: str, top_k: int):
        return [
            {
                "content": "The knowledge base refreshes itself on a schedule.",
                "metadata": {"location": "knowledge.txt"},
            }
        ]


class FakeLLM:
    def answer(self, question: str, contexts: list[str]) -> str:
        return f"LLM answer for: {question} | {contexts[0]}"


def test_chatbot_uses_llm_when_available(tmp_path: Path):
    config = AppConfig(
        poll_interval_minutes=60,
        chunk_size=100,
        chunk_overlap=10,
        top_k=3,
        vector_store_dir=tmp_path / "chroma",
        metadata_db_path=tmp_path / "state.db",
        source_timeout_seconds=5,
        source_max_retries=2,
        source_retry_backoff_seconds=0.0,
        llm=LLMConfig(api_key="key", model="model", base_url="http://test", timeout_seconds=5, max_retries=1),
        auth=AuthConfig(api_key=None, admin_key=None),
        sources=[],
    )
    monitor = AppMonitor()
    chatbot = RetrievalChatbot(config, FakeVectorStore(), monitor, FakeLLM())

    response = chatbot.answer("How does it update?")

    assert response.used_llm is True
    assert "LLM answer for: How does it update?" in response.answer
    assert response.sources == ["knowledge.txt"]
    assert monitor.snapshot()["llm_calls"] == 1
