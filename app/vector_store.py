from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from app.config import AppConfig
from app.preprocessing import tokenize_and_lemmatize
from app.retrieval import BM25Retriever, ReciprocalRankFusion, RetrievalChunk


def _tokenize(text: str) -> list[str]:
    return tokenize_and_lemmatize(text)


class _LocalPersistentVectorStore:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.storage_path = self.storage_dir / "local_store.json"
        self._records = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if not self.storage_path.exists():
            return []
        return json.loads(self.storage_path.read_text(encoding="utf-8"))

    def _persist(self) -> None:
        self.storage_path.write_text(json.dumps(self._records, indent=2), encoding="utf-8")

    def replace_source_chunks(self, source_id: str, chunks: list[str], location: str) -> None:
        self._records = [record for record in self._records if record["source_id"] != source_id]
        for index, chunk in enumerate(chunks):
            self._records.append(
                {
                    "id": f"{source_id}:{index}",
                    "source_id": source_id,
                    "location": location,
                    "chunk_index": index,
                    "content": chunk,
                }
            )
        self._persist()

    def search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []
        for record in self._records:
            content_tokens = _tokenize(record["content"])
            score = self._cosine_score(query_tokens, content_tokens)
            if score > 0:
                scored.append((score, record))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "content": record["content"],
                "_score": score,
                "metadata": {
                    "location": record["location"],
                    "source_id": record["source_id"],
                    "chunk_index": record["chunk_index"],
                },
            }
            for _, record in scored[:top_k]
        ]

    def _cosine_score(self, query_tokens: list[str], content_tokens: list[str]) -> float:
        query_counts: dict[str, int] = {}
        content_counts: dict[str, int] = {}
        for token in query_tokens:
            query_counts[token] = query_counts.get(token, 0) + 1
        for token in content_tokens:
            content_counts[token] = content_counts.get(token, 0) + 1

        overlap = set(query_counts).intersection(content_counts)
        numerator = sum(query_counts[token] * content_counts[token] for token in overlap)
        query_norm = math.sqrt(sum(value * value for value in query_counts.values()))
        content_norm = math.sqrt(sum(value * value for value in content_counts.values()))
        if not numerator or not query_norm or not content_norm:
            return 0.0
        return numerator / (query_norm * content_norm)


class VectorStore:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.retrieval_mode = getattr(config, "retrieval_mode", "legacy").lower()
        self.bm25_k1 = getattr(config, "bm25_k1", 1.2)
        self.bm25_b = getattr(config, "bm25_b", 0.75)
        self.rrf_k = getattr(config, "rrf_k", 60)

        backend = os.getenv("VECTOR_STORE_BACKEND", "").lower()
        if backend == "local":
            self._store = _LocalPersistentVectorStore(config.vector_store_dir)
            return

        try:
            import chromadb
            from chromadb.utils import embedding_functions

            config.vector_store_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(config.vector_store_dir))
            self._store = client.get_or_create_collection(
                name="knowledge_base",
                embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                ),
            )
        except Exception:
            self._store = _LocalPersistentVectorStore(config.vector_store_dir)

    def _local_records(self) -> list[dict[str, Any]]:
        if hasattr(self._store, "_records"):
            return list(self._store._records)
        return []

    def _bm25_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        records = self._local_records()
        if not records:
            return []

        chunks = [
            RetrievalChunk(
                chunk_id=str(record.get("id", f"chunk-{index}")),
                content=str(record.get("content", "")),
                metadata={
                    "location": record.get("location", ""),
                    "source_id": record.get("source_id", ""),
                    "chunk_index": record.get("chunk_index", index),
                },
            )
            for index, record in enumerate(records)
        ]
        retriever = BM25Retriever(chunks, k1=self.bm25_k1, b=self.bm25_b)
        ranked = retriever.search(query, top_k=top_k)
        return [
            {
                "content": item.chunk.content,
                "_score": item.score,
                "metadata": {
                    **item.chunk.metadata,
                    "location": item.chunk.metadata.get("location", ""),
                    "source_id": item.chunk.metadata.get("source_id", ""),
                    "chunk_index": item.chunk.metadata.get("chunk_index", 0),
                },
            }
            for item in ranked
        ]

    def _hybrid_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        records = self._local_records()
        if not records:
            return []

        chunks = [
            RetrievalChunk(
                chunk_id=str(record.get("id", f"chunk-{index}")),
                content=str(record.get("content", "")),
                metadata={
                    "location": record.get("location", ""),
                    "source_id": record.get("source_id", ""),
                    "chunk_index": record.get("chunk_index", index),
                },
            )
            for index, record in enumerate(records)
        ]
        ranked_bm25 = BM25Retriever(chunks, k1=self.bm25_k1, b=self.bm25_b).search(query, top_k=max(10, top_k))
        legacy = [
            {
                "content": chunk.content,
                "_score": 1.0,
                "metadata": {**chunk.metadata},
            }
            for chunk in chunks
        ]
        local_ranked = []
        for record in records:
            content = str(record.get("content", ""))
            if not content:
                continue
            local_ranked.append(
                type("_Match", (), {"chunk": RetrievalChunk(chunk_id=str(record.get("id", "unknown")), content=content, metadata={"location": record.get("location", ""), "source_id": record.get("source_id", ""), "chunk_index": record.get("chunk_index", 0)}), "rank": 1, "score": 0.5, "retriever": "local"})
            )
        fused = ReciprocalRankFusion(rrf_k=self.rrf_k).fuse([ranked_bm25, local_ranked], top_k=top_k)
        return [
            {
                "content": item.chunk.content,
                "_score": item.score,
                "metadata": {**item.chunk.metadata},
            }
            for item in fused
        ]

    def replace_source_chunks(self, source_id: str, chunks: list[str], location: str) -> None:
        if hasattr(self._store, "get") and hasattr(self._store, "delete") and hasattr(self._store, "add"):
            existing = self._store.get(where={"source_id": source_id})
            ids = existing.get("ids", [])
            if ids:
                self._store.delete(ids=ids)
            if chunks:
                chunk_ids = [f"{source_id}:{index}" for index, _ in enumerate(chunks)]
                metadatas = [
                    {"source_id": source_id, "location": location, "chunk_index": index}
                    for index, _ in enumerate(chunks)
                ]
                self._store.add(ids=chunk_ids, documents=chunks, metadatas=metadatas)
            return

        self._store.replace_source_chunks(source_id, chunks, location)

    def search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        if self.retrieval_mode == "bm25":
            return self._bm25_search(query, top_k)
        if self.retrieval_mode in {"hybrid", "hybrid_rerank"}:
            return self._hybrid_search(query, top_k)

        if hasattr(self._store, "query"):
            result = self._store.query(query_texts=[query], n_results=top_k)
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0] or [0.0] * len(documents)
            return [
                {
                    "content": document,
                    "metadata": metadata,
                    # Chroma's standard distance is cosine distance; retain a
                    # normalized similarity for the relevance guard.
                    "_score": max(0.0, 1.0 - float(distance)),
                }
                for document, metadata, distance in zip(documents, metadatas, distances, strict=False)
            ]

        if hasattr(self._store, "_records"):
            return self._store.search(query, top_k)

        return self._store.search(query, top_k)
