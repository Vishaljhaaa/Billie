from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import AppConfig
from app.preprocessing import tokenize_and_lemmatize
from app.sources import SourceLoader
from app.text_utils import chunk_text

DATASET_PATH = PROJECT_ROOT / "experiments" / "benchmark_dataset.json"
RESULTS_DIR = PROJECT_ROOT / "artifacts"


def tokenize(text: str) -> list[str]:
    return tokenize_and_lemmatize(text)


@dataclass(frozen=True)
class ChunkRecord:
    source_id: str
    chunk_id: str
    text: str


class KeywordOverlapRetriever:
    def __init__(self, chunks: list[ChunkRecord]) -> None:
        self.chunks = chunks

    def search(self, question: str, top_k: int) -> list[ChunkRecord]:
        query_tokens = set(tokenize(question))
        scored = []
        for chunk in self.chunks:
            overlap = len(query_tokens.intersection(tokenize(chunk.text)))
            scored.append((overlap, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for score, chunk in scored[:top_k] if score > 0]


class CosineRetriever:
    def __init__(self, chunks: list[ChunkRecord]) -> None:
        self.chunks = chunks

    def search(self, question: str, top_k: int) -> list[ChunkRecord]:
        question_tokens = tokenize(question)
        scored = []
        for chunk in self.chunks:
            score = self._score(question_tokens, tokenize(chunk.text))
            scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for score, chunk in scored[:top_k] if score > 0]

    def _score(self, left: list[str], right: list[str]) -> float:
        left_counts = self._counts(left)
        right_counts = self._counts(right)
        overlap = set(left_counts).intersection(right_counts)
        numerator = sum(left_counts[token] * right_counts[token] for token in overlap)
        left_norm = math.sqrt(sum(value * value for value in left_counts.values()))
        right_norm = math.sqrt(sum(value * value for value in right_counts.values()))
        if numerator == 0 or left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)

    def _counts(self, tokens: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        return counts


def build_chunks(config: AppConfig, include_remote: bool = False) -> list[ChunkRecord]:
    loader = SourceLoader.from_config(config)
    chunks: list[ChunkRecord] = []
    for source in config.sources:
        if source.type == "url" and not include_remote:
            continue
        document = loader.load(source)
        for index, text in enumerate(
            chunk_text(document.content, config.chunk_size, config.chunk_overlap)
        ):
            chunks.append(ChunkRecord(source_id=source.id, chunk_id=f"{source.id}:{index}", text=text))
    return chunks


def keyword_recall(text: str, expected_keywords: list[str]) -> float:
    lowered = text.lower()
    hits = sum(1 for keyword in expected_keywords if keyword.lower() in lowered)
    return hits / max(1, len(expected_keywords))


def evaluate(name: str, retriever, benchmark_rows: list[dict[str, object]]) -> dict[str, float | str]:
    top1_hits = 0
    top3_hits = 0
    keyword_recalls: list[float] = []

    for row in benchmark_rows:
        results = retriever.search(str(row["question"]), top_k=3)
        source_ids = [chunk.source_id for chunk in results]
        expected_source = str(row["expected_source"])
        if source_ids[:1] == [expected_source]:
            top1_hits += 1
        if expected_source in source_ids:
            top3_hits += 1
        combined_text = " ".join(chunk.text for chunk in results)
        keyword_recalls.append(keyword_recall(combined_text, list(row["expected_keywords"])))

    total = len(benchmark_rows)
    return {
        "model": name,
        "top1_accuracy": round(top1_hits / total, 3),
        "top3_accuracy": round(top3_hits / total, 3),
        "avg_keyword_recall": round(sum(keyword_recalls) / total, 3),
    }


def save_bar_chart(title: str, results: list[dict[str, float | str]], metric: str, output_name: str) -> None:
    models = [str(item["model"]) for item in results]
    values = [float(item[metric]) for item in results]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(models, values, color=["#B85C38", "#3B6B7A"])
    plt.ylim(0, 1.05)
    plt.title(title)
    plt.ylabel(metric.replace("_", " ").title())
    for bar, value in zip(bars, values, strict=False):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 0.02, f"{value:.2f}", ha="center")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / output_name, dpi=180)
    plt.close()


def run() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config = AppConfig.load(PROJECT_ROOT / "sources.json")
    benchmark_rows = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    baseline_config = AppConfig(
        poll_interval_minutes=config.poll_interval_minutes,
        chunk_size=220,
        chunk_overlap=0,
        top_k=config.top_k,
        memory_window=config.memory_window,
        vector_store_dir=config.vector_store_dir,
        metadata_db_path=config.metadata_db_path,
        session_store_path=config.session_store_path,
        source_timeout_seconds=config.source_timeout_seconds,
        source_max_retries=config.source_max_retries,
        source_retry_backoff_seconds=config.source_retry_backoff_seconds,
        llm=config.llm,
        auth=config.auth,
        sources=config.sources,
    )
    improved_config = AppConfig(
        poll_interval_minutes=config.poll_interval_minutes,
        chunk_size=220,
        chunk_overlap=60,
        top_k=config.top_k,
        memory_window=config.memory_window,
        vector_store_dir=config.vector_store_dir,
        metadata_db_path=config.metadata_db_path,
        session_store_path=config.session_store_path,
        source_timeout_seconds=config.source_timeout_seconds,
        source_max_retries=config.source_max_retries,
        source_retry_backoff_seconds=config.source_retry_backoff_seconds,
        llm=config.llm,
        auth=config.auth,
        sources=config.sources,
    )

    baseline_chunks = build_chunks(baseline_config, include_remote=False)
    improved_chunks = build_chunks(improved_config, include_remote=False)

    results = [
        evaluate("KeywordOverlap", KeywordOverlapRetriever(baseline_chunks), benchmark_rows),
        evaluate("CosineOverlap", CosineRetriever(improved_chunks), benchmark_rows),
    ]

    (RESULTS_DIR / "benchmark_results.json").write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )
    save_bar_chart(
        "Retriever Top-1 Accuracy Comparison",
        results,
        metric="top1_accuracy",
        output_name="retriever_top1_accuracy.png",
    )
    save_bar_chart(
        "Retriever Keyword Recall Comparison",
        results,
        metric="avg_keyword_recall",
        output_name="retriever_keyword_recall.png",
    )


if __name__ == "__main__":
    run()
