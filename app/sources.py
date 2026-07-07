from __future__ import annotations

import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from app.config import AppConfig, SourceConfig
from app.schemas import SourceDocument
from app.text_utils import sha256_text


class SourceLoader:
    def __init__(
        self,
        timeout_seconds: float = 20.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.5,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds

    @classmethod
    def from_config(cls, config: AppConfig) -> "SourceLoader":
        return cls(
            timeout_seconds=config.source_timeout_seconds,
            max_retries=config.source_max_retries,
            retry_backoff_seconds=config.source_retry_backoff_seconds,
        )

    def load(self, source: SourceConfig) -> SourceDocument:
        if source.type == "file":
            return self._load_file(source)
        if source.type == "url":
            return self._load_url(source)
        raise ValueError(f"Unsupported source type: {source.type}")

    def _load_file(self, source: SourceConfig) -> SourceDocument:
        if not source.path:
            raise ValueError(f"Missing path for source '{source.id}'")

        path = Path(source.path)
        content = path.read_text(encoding="utf-8")
        return SourceDocument(
            source_id=source.id,
            content=content,
            location=str(path),
            fingerprint=sha256_text(content),
        )

    def _load_url(self, source: SourceConfig) -> SourceDocument:
        if not source.url:
            raise ValueError(f"Missing url for source '{source.id}'")

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
                    response = client.get(
                        source.url,
                        headers={"User-Agent": "dynamic-kb-chatbot/1.0"},
                    )
                    response.raise_for_status()
                return self._html_to_document(source, response.text)
            except Exception as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                time.sleep(self.retry_backoff_seconds * attempt)

        raise RuntimeError(f"Failed to load source '{source.id}' after retries.") from last_error

    def _html_to_document(self, source: SourceConfig, html: str) -> SourceDocument:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        content = soup.get_text(separator=" ", strip=True)

        return SourceDocument(
            source_id=source.id,
            content=content,
            location=source.url or "",
            fingerprint=sha256_text(content),
        )
