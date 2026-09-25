from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Protocol


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class RetrievalChunk:
    chunk_id: str
    content: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class RankedChunk:
    chunk: RetrievalChunk
    rank: int
    score: float
    retriever: str


class Retriever(Protocol):
    def search(self, query: str, top_k: int) -> list[RankedChunk]:
        ...


def retrieval_tokens(text: str) -> list[str]:
    """Versioned BM25 tokenizer: lowercase ASCII alphanumeric terms; punctuation separates."""
    return _TOKEN_PATTERN.findall(text.casefold())


class BM25Retriever:
    """BM25Okapi retriever over an immutable snapshot of indexed chunks."""

    name = "bm25"

    def __init__(
        self,
        chunks: list[RetrievalChunk],
        *,
        k1: float = 1.2,
        b: float = 0.75,
    ) -> None:
        if k1 < 0:
            raise ValueError("k1 must be non-negative")
        if not 0.0 <= b <= 1.0:
            raise ValueError("b must be between 0 and 1")
        self.k1 = float(k1)
        self.b = float(b)
        self.chunks = tuple(chunks)
        self._term_frequencies: list[Counter[str]] = []
        self._document_frequencies: Counter[str] = Counter()
        self._document_lengths: list[int] = []
        self._postings: dict[str, list[int]] = defaultdict(list)

        for index, chunk in enumerate(self.chunks):
            frequencies = Counter(retrieval_tokens(chunk.content))
            self._term_frequencies.append(frequencies)
            self._document_lengths.append(sum(frequencies.values()))
            for term in frequencies:
                self._document_frequencies[term] += 1
                self._postings[term].append(index)

        self._average_document_length = (
            sum(self._document_lengths) / len(self._document_lengths)
            if self._document_lengths
            else 0.0
        )

    def search(self, query: str, top_k: int = 4) -> list[RankedChunk]:
        if top_k <= 0:
            return []
        query_terms = retrieval_tokens(query)
        if not query_terms or not self.chunks:
            return []

        # Query term frequency is retained: repeated query terms contribute repeatedly.
        candidates = sorted({index for term in query_terms for index in self._postings.get(term, ())})
        scored: list[tuple[float, str, int]] = []
        for index in candidates:
            score = self.score_document(query_terms, index)
            if score > 0.0:
                scored.append((score, self.chunks[index].chunk_id, index))

        # Stable chunk ID is the deterministic tie-break, independent of input order.
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [
            RankedChunk(
                chunk=self.chunks[index],
                rank=rank,
                score=score,
                retriever=self.name,
            )
            for rank, (score, _chunk_id, index) in enumerate(scored[:top_k], start=1)
        ]

    def score_document(self, query_terms: list[str], document_index: int) -> float:
        if not self.chunks:
            return 0.0
        frequencies = self._term_frequencies[document_index]
        document_length = self._document_lengths[document_index]
        average_length = self._average_document_length
        length_norm = 1.0 - self.b + self.b * document_length / average_length if average_length else 1.0
        score = 0.0
        document_count = len(self.chunks)
        for term in query_terms:
            frequency = frequencies.get(term, 0)
            if frequency == 0:
                continue
            document_frequency = self._document_frequencies[term]
            inverse_document_frequency = math.log(
                1.0 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            denominator = frequency + self.k1 * length_norm
            if denominator:
                score += inverse_document_frequency * frequency * (self.k1 + 1.0) / denominator
        return score


class ReciprocalRankFusion:
    """Fuse independently ranked candidates without comparing raw scores."""

    def __init__(self, *, rrf_k: int = 60) -> None:
        if rrf_k <= 0:
            raise ValueError("rrf_k must be positive")
        self.rrf_k = rrf_k

    def fuse(self, rankings: list[list[RankedChunk]], top_k: int = 4) -> list[RankedChunk]:
        if top_k <= 0:
            return []
        fused: dict[str, tuple[RetrievalChunk, float, dict[str, int], dict[str, float]]] = {}
        for ranking in rankings:
            for item in ranking:
                chunk_id = item.chunk.chunk_id
                if chunk_id not in fused:
                    fused[chunk_id] = (item.chunk, 0.0, {}, {})
                chunk, score, ranks, component_scores = fused[chunk_id]
                score += 1.0 / (self.rrf_k + item.rank)
                ranks[item.retriever] = item.rank
                component_scores[item.retriever] = item.score
                fused[chunk_id] = (chunk, score, ranks, component_scores)

        ordered = sorted(fused.items(), key=lambda item: (-item[1][1], item[0]))[:top_k]
        return [
            RankedChunk(
                chunk=RetrievalChunk(
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    metadata={
                        **chunk.metadata,
                        "component_ranks": ranks,
                        "component_scores": component_scores,
                        "rrf_score": score,
                    },
                ),
                rank=rank,
                score=score,
                retriever="rrf",
            )
            for rank, (_chunk_id, (chunk, score, ranks, component_scores)) in enumerate(ordered, start=1)
        ]
