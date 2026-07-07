from __future__ import annotations

import hashlib


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []

    step = max(1, chunk_size - chunk_overlap)
    chunks: list[str] = []

    for start in range(0, len(normalized), step):
        chunk = normalized[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(normalized):
            break

    return chunks
