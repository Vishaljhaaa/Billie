from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any

from app.config import AppConfig


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


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
        if hasattr(self._store, "query"):
            result = self._store.query(query_texts=[query], n_results=top_k)
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            return [
                {"content": document, "metadata": metadata}
                for document, metadata in zip(documents, metadatas, strict=False)
            ]

        return self._store.search(query, top_k)
