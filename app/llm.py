from __future__ import annotations

import base64
import mimetypes
import time
from typing import Any, Protocol

import httpx

from app.config import LLMConfig


class LLMClient(Protocol):
    def answer(self, question: str, contexts: list[str]) -> str:
        ...

    def answer_multimodal(
        self,
        question: str,
        *,
        text_contexts: list[str],
        visual_contexts: list[str],
        conversation_context: list[dict[str, Any]],
    ) -> str:
        ...

    def analyze_image(self, question: str, image_path: str, description: str | None = None) -> dict[str, Any]:
        ...


class OpenAICompatibleLLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def answer(self, question: str, contexts: list[str]) -> str:
        return self.answer_multimodal(
            question,
            text_contexts=contexts,
            visual_contexts=[],
            conversation_context=[],
        )

    def answer_multimodal(
        self,
        question: str,
        *,
        text_contexts: list[str],
        visual_contexts: list[str],
        conversation_context: list[dict[str, Any]],
    ) -> str:
        if not self.enabled:
            raise RuntimeError("LLM client is not configured.")

        system_prompt = (
            "You are a retrieval-augmented multimodal assistant. Answer only with the supplied text, "
            "visual evidence, and recent conversation state. If the evidence is ambiguous or insufficient, "
            "say so clearly instead of guessing."
        )
        text_context_block = "\n\n".join(
            f"Source snippet {index + 1}:\n{context}"
            for index, context in enumerate(text_contexts)
        )
        visual_context_block = "\n\n".join(
            f"Visual evidence {index + 1}:\n{context}"
            for index, context in enumerate(visual_contexts)
        )
        conversation_block = "\n\n".join(
            f"Turn {index + 1} question: {turn.get('question', '')}\n"
            f"Turn {index + 1} answer: {turn.get('answer', '')}"
            for index, turn in enumerate(conversation_context)
        )
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\n"
                        f"Recent conversation:\n{conversation_block or 'None'}\n\n"
                        f"Retrieved text context:\n{text_context_block or 'None'}\n\n"
                        f"Visual observations:\n{visual_context_block or 'None'}\n\n"
                        "Write a concise answer with evidence-based reasoning and mention uncertainty if needed."
                    ),
                },
            ],
            "temperature": 0.2,
        }

        return self._run_request(payload)

    def analyze_image(self, question: str, image_path: str, description: str | None = None) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LLM client is not configured.")

        image_bytes = open(image_path, "rb").read()
        media_type = mimetypes.guess_type(image_path)[0] or "image/png"
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        prompt = (
            "Inspect this image and return JSON with keys: summary, evidence, entities, ambiguities, confidence. "
            "Use evidence as a list of short factual observations and ambiguities as a list. "
            f"Question focus: {question}. "
            f"Extra user hint: {description or 'None'}."
        )
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{encoded}",
                            },
                        },
                    ],
                }
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        return self._run_request(payload, expect_json=True)

    def _run_request(self, payload: dict[str, Any], expect_json: bool = False) -> Any:
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
                content = body["choices"][0]["message"]["content"]
                if isinstance(content, list):
                    content = "".join(
                        item.get("text", "") if isinstance(item, dict) else str(item)
                        for item in content
                    )
                content = str(content).strip()
                if expect_json:
                    import json

                    return json.loads(content)
                return content
            except Exception as exc:
                last_error = exc
                if attempt == self.config.max_retries:
                    break
                time.sleep(min(8.0, 2 ** (attempt - 1)))

        raise RuntimeError("LLM request failed after retries.") from last_error
