from __future__ import annotations

import time
from typing import Protocol

import httpx

from app.config import LLMConfig


class LLMClient(Protocol):
    def answer(self, question: str, contexts: list[str]) -> str:
        ...


class OpenAICompatibleLLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def answer(self, question: str, contexts: list[str]) -> str:
        if not self.enabled:
            raise RuntimeError("LLM client is not configured.")

        system_prompt = (
            "You are a retrieval-augmented assistant. Answer only with the provided context. "
            "If the context is insufficient, say so clearly."
        )
        context_block = "\n\n".join(
            f"Source snippet {index + 1}:\n{context}"
            for index, context in enumerate(contexts)
        )
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\n"
                        f"Retrieved context:\n{context_block}\n\n"
                        "Write a concise answer and mention uncertainty if needed."
                    ),
                },
            ],
            "temperature": 0.2,
        }

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                with httpx.Client(
                    timeout=self.config.timeout_seconds,
                    follow_redirects=True,
                ) as client:
                    response = client.post(
                        f"{self.config.base_url.rstrip('/')}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                body = response.json()
                return body["choices"][0]["message"]["content"].strip()
            except Exception as exc:
                last_error = exc
                if attempt == self.config.max_retries:
                    break
                time.sleep(min(8.0, 2 ** (attempt - 1)))

        raise RuntimeError("LLM request failed after retries.") from last_error
