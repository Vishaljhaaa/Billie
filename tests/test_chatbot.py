from __future__ import annotations

from pathlib import Path

from app.chatbot import RetrievalChatbot
from app.config import AppConfig, AuthConfig, LLMConfig
from app.memory import ConversationMemoryStore
from app.monitoring import AppMonitor
from app.schemas import ImageInput


class FakeVectorStore:
    def __init__(self) -> None:
        self.last_query = ""

    def search(self, query: str, top_k: int):
        self.last_query = query
        return [
            {
                "content": "The knowledge base refreshes itself on a schedule.",
                "metadata": {"location": "knowledge.txt"},
            }
        ]


class FakeLLM:
    def answer(self, question: str, contexts: list[str]) -> str:
        return f"LLM answer for: {question} | {contexts[0]}"

    def answer_multimodal(self, question: str, *, text_contexts, visual_contexts, conversation_context) -> str:
        return f"LLM answer for: {question} | {text_contexts[0]}"

    def analyze_image(self, question: str, image_path: str, description: str | None = None) -> dict[str, object]:
        return {"summary": f"Visual cue for {question}", "evidence": ["Generated from fake LLM"], "confidence": 0.7}


def test_chatbot_uses_llm_when_available(tmp_path: Path):
    config = AppConfig(
        poll_interval_minutes=60,
        chunk_size=100,
        chunk_overlap=10,
        top_k=3,
        memory_window=4,
        vector_store_dir=tmp_path / "chroma",
        metadata_db_path=tmp_path / "state.db",
        session_store_path=tmp_path / "sessions.json",
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


def test_chatbot_uses_visual_sidecar_and_memory(tmp_path: Path):
    image_path = tmp_path / "notice.png"
    image_path.write_bytes(b"placeholder")
    image_path.with_suffix(".json").write_text(
        """
        {
          "summary": "The notice says to report phishing to security@company.test.",
          "evidence": ["Reporting inbox is security@company.test"],
          "entities": ["security@company.test"],
          "confidence": 0.94
        }
        """.strip(),
        encoding="utf-8",
    )
    config = AppConfig(
        poll_interval_minutes=60,
        chunk_size=100,
        chunk_overlap=10,
        top_k=3,
        memory_window=4,
        vector_store_dir=tmp_path / "chroma",
        metadata_db_path=tmp_path / "state.db",
        session_store_path=tmp_path / "sessions.json",
        source_timeout_seconds=5,
        source_max_retries=2,
        source_retry_backoff_seconds=0.0,
        llm=LLMConfig(api_key=None, model="model", base_url="http://test", timeout_seconds=5, max_retries=1),
        auth=AuthConfig(api_key=None, admin_key=None),
        sources=[],
    )
    monitor = AppMonitor()
    chatbot = RetrievalChatbot(
        config,
        FakeVectorStore(),
        monitor,
        None,
        memory_store=ConversationMemoryStore(config.session_store_path),
    )

    first = chatbot.answer(
        "Where should I report OTP phishing?",
        session_id="security-thread",
        image_inputs=[ImageInput(path=str(image_path))],
    )
    second = chatbot.answer("Can you repeat the reporting email?", session_id="security-thread")

    assert "security@company.test" in first.answer
    assert first.evidence[1].modality == "image"
    assert second.session_id == "security-thread"
    assert "security@company.test" in second.answer


def test_chatbot_adapts_answer_for_negative_sentiment(tmp_path: Path):
    config = AppConfig(
        poll_interval_minutes=60,
        chunk_size=100,
        chunk_overlap=10,
        top_k=3,
        memory_window=4,
        vector_store_dir=tmp_path / "chroma",
        metadata_db_path=tmp_path / "state.db",
        session_store_path=tmp_path / "sessions.json",
        source_timeout_seconds=5,
        source_max_retries=2,
        source_retry_backoff_seconds=0.0,
        llm=LLMConfig(api_key=None, model="model", base_url="http://test", timeout_seconds=5, max_retries=1),
        auth=AuthConfig(api_key=None, admin_key=None),
        sources=[],
    )
    chatbot = RetrievalChatbot(config, FakeVectorStore(), AppMonitor(), None)

    response = chatbot.answer("I am frustrated. How does it update?")

    assert response.sentiment is not None
    assert response.sentiment.label == "negative"
    assert response.answer.startswith("I understand this is frustrating.")


def test_chatbot_preserves_context_across_language_switch(tmp_path: Path):
    config = AppConfig(
        poll_interval_minutes=60,
        chunk_size=100,
        chunk_overlap=10,
        top_k=3,
        memory_window=4,
        vector_store_dir=tmp_path / "chroma",
        metadata_db_path=tmp_path / "state.db",
        session_store_path=tmp_path / "sessions.json",
        source_timeout_seconds=5,
        source_max_retries=2,
        source_retry_backoff_seconds=0.0,
        llm=LLMConfig(api_key=None, model="model", base_url="http://test", timeout_seconds=5, max_retries=1),
        auth=AuthConfig(api_key=None, admin_key=None),
        sources=[],
    )
    vector_store = FakeVectorStore()
    chatbot = RetrievalChatbot(config, vector_store, AppMonitor(), None)

    first = chatbot.answer("Como actualiza la base de conocimiento?", session_id="lang-thread")
    second = chatbot.answer("ज्ञान बेस कैसे अपडेट होता है?", session_id="lang-thread")

    assert first.language is not None
    assert first.language.primary_language == "es"
    assert "update" in first.language.normalized_query
    assert second.language is not None
    assert second.language.primary_language == "hi"
    assert second.answer.startswith("हिंदी उत्तर:")
    assert "update" in vector_store.last_query


def test_chatbot_requests_clarification_for_ambiguous_visual_evidence(tmp_path: Path):
    image_path = tmp_path / "schedule.png"
    image_path.write_bytes(b"placeholder")
    image_path.with_suffix(".json").write_text(
        '{"summary":"Two launches are shown.","entities":["Alpha","Beta"],"ambiguities":["Two dates are visible for different launches."]}',
        encoding="utf-8",
    )
    config = AppConfig(
        poll_interval_minutes=60, chunk_size=100, chunk_overlap=10, top_k=3, memory_window=4,
        vector_store_dir=tmp_path / "chroma", metadata_db_path=tmp_path / "state.db", session_store_path=tmp_path / "sessions.json",
        source_timeout_seconds=5, source_max_retries=1, source_retry_backoff_seconds=0,
        llm=LLMConfig(api_key=None, model="model", base_url="http://test", timeout_seconds=5, max_retries=1),
        auth=AuthConfig(api_key=None, admin_key=None), sources=[],
    )
    response = RetrievalChatbot(config, FakeVectorStore(), AppMonitor()).answer(
        "What date does it start?", image_inputs=[ImageInput(path=str(image_path))]
    )

    assert response.needs_clarification is True
    assert response.follow_up_question == "Which item in the image would you like me to focus on?"
    assert response.validation is not None
    assert response.validation.grounded is True


def test_chatbot_rejects_generic_web_match_for_unrelated_question(tmp_path: Path):
    class IrrelevantWebMatch:
        def search(self, query: str, top_k: int):
            return [{
                "content": "Python.org documentation has a general how-to guide.",
                "_score": 0.04,
                "metadata": {"location": "https://www.python.org/blogs/"},
            }]

    config = AppConfig(
        poll_interval_minutes=60, chunk_size=100, chunk_overlap=10, top_k=3, memory_window=4,
        vector_store_dir=tmp_path / "chroma", metadata_db_path=tmp_path / "state.db", session_store_path=tmp_path / "sessions.json",
        source_timeout_seconds=5, source_max_retries=1, source_retry_backoff_seconds=0,
        llm=LLMConfig(api_key=None, model="model", base_url="http://test", timeout_seconds=5, max_retries=1),
        auth=AuthConfig(api_key=None, admin_key=None), sources=[],
    )
    response = RetrievalChatbot(config, IrrelevantWebMatch(), AppMonitor()).answer("How do I bake a cake?")

    assert "couldn't find relevant" in response.answer.lower()
    assert response.sources == []
