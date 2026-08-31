from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class SourceDocument:
    source_id: str
    content: str
    location: str
    fingerprint: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=3)
    session_id: str = Field(default="default", min_length=1)
    mode: Literal["general", "medical", "research"] = "general"
    image_inputs: list["ImageInput"] = Field(default_factory=list)


class ImageInput(BaseModel):
    path: str = Field(min_length=1)
    description: str | None = None


class EvidenceItem(BaseModel):
    modality: str
    source: str
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    details: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    grounded: bool
    confidence: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)


class SentimentPayload(BaseModel):
    label: str
    score: float = Field(ge=0.0, le=1.0)
    positive_hits: list[str] = Field(default_factory=list)
    negative_hits: list[str] = Field(default_factory=list)


class LanguagePayload(BaseModel):
    primary_language: str
    language_name: str
    detected_languages: list[str] = Field(default_factory=list)
    mixed_language: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    normalized_query: str
    ambiguous: bool = False
    notes: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    mode: str = "general"
    used_llm: bool = False
    session_id: str = "default"
    sentiment: SentimentPayload | None = None
    language: LanguagePayload | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    needs_clarification: bool = False
    follow_up_question: str | None = None
    validation: ValidationResult | None = None


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
