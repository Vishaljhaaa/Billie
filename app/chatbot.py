from __future__ import annotations

from app.config import AppConfig
from app.llm import LLMClient
from app.monitoring import AppMonitor
from app.schemas import ChatResponse
from app.vector_store import VectorStore


class RetrievalChatbot:
    def __init__(
        self,
        config: AppConfig,
        vector_store: VectorStore,
        monitor: AppMonitor,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.config = config
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.monitor = monitor

    def answer(self, question: str) -> ChatResponse:
        self.monitor.record_chat()
        matches = self.vector_store.search(question, top_k=self.config.top_k)
        if not matches:
            return ChatResponse(
                answer="I couldn't find relevant knowledge in the current vector database.",
                sources=[],
                used_llm=False,
            )

        snippets = [match["content"] for match in matches]
        sources = list(dict.fromkeys(match["metadata"]["location"] for match in matches))

        if self.llm_client is not None:
            try:
                answer = self.llm_client.answer(question, snippets)
                self.monitor.record_llm_success()
                return ChatResponse(answer=answer, sources=sources, used_llm=True)
            except Exception:
                self.monitor.record_llm_failure()

        answer = self._compose_fallback_answer(question, snippets)
        return ChatResponse(answer=answer, sources=sources, used_llm=False)

    def _compose_fallback_answer(self, question: str, snippets: list[str]) -> str:
        joined = " ".join(snippets[:2]).strip()
        return (
            f"Question: {question}\n\n"
            "The LLM was unavailable, so this answer is based on direct retrieval snippets:\n"
            f"{joined}"
        )
