from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class SourceConfig:
    id: str
    type: str
    path: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class LLMConfig:
    api_key: str | None
    model: str
    base_url: str
    timeout_seconds: float
    max_retries: int

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)


@dataclass(frozen=True)
class AuthConfig:
    api_key: str | None
    admin_key: str | None


@dataclass(frozen=True)
class AppConfig:
    poll_interval_minutes: int
    chunk_size: int
    chunk_overlap: int
    top_k: int
    memory_window: int
    vector_store_dir: Path
    metadata_db_path: Path
    session_store_path: Path
    source_timeout_seconds: float
    source_max_retries: int
    source_retry_backoff_seconds: float
    llm: LLMConfig
    auth: AuthConfig
    sources: list[SourceConfig]

    @classmethod
    def load(cls, path: str | Path = "sources.json") -> "AppConfig":
        config_path = Path(path)
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        root = config_path.parent.resolve()
        sources: list[SourceConfig] = []

        for item in payload["sources"]:
            source_path = item.get("path")
            normalized = {
                **item,
                "path": str((root / source_path).resolve()) if source_path else None,
            }
            sources.append(SourceConfig(**normalized))

        return cls(
            poll_interval_minutes=payload["poll_interval_minutes"],
            chunk_size=payload["chunk_size"],
            chunk_overlap=payload["chunk_overlap"],
            top_k=payload["top_k"],
            memory_window=payload.get("memory_window", 4),
            vector_store_dir=(root / payload["vector_store_dir"]).resolve(),
            metadata_db_path=(root / payload["metadata_db_path"]).resolve(),
            session_store_path=(root / payload.get("session_store_path", "data/session_memory.json")).resolve(),
            source_timeout_seconds=float(os.getenv("SOURCE_TIMEOUT_SECONDS", "20")),
            source_max_retries=int(os.getenv("SOURCE_MAX_RETRIES", "3")),
            source_retry_backoff_seconds=float(os.getenv("SOURCE_RETRY_BACKOFF_SECONDS", "1.5")),
            llm=LLMConfig(
                api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
                max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3")),
            ),
            auth=AuthConfig(
                api_key=os.getenv("CHATBOT_API_KEY"),
                admin_key=os.getenv("CHATBOT_ADMIN_API_KEY"),
            ),
            sources=sources,
        )
