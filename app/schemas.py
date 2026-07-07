from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class SourceDocument:
    source_id: str
    content: str
    location: str
    fingerprint: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=3)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    used_llm: bool = False


class SyncResponse(BaseModel):
    updated_sources: list[str]
    skipped_sources: list[str]
    failed_sources: list[str] = Field(default_factory=list)
    error_details: dict[str, str] = Field(default_factory=dict)


class SourceStatus(BaseModel):
    source_id: str
    fingerprint: str
    updated_at: str


class AdminStatusResponse(BaseModel):
    last_sync_at: str | None
    source_count: int
    indexed_sources: list[SourceStatus]
    last_sync_summary: SyncResponse | None
    metrics: dict[str, float | int]
