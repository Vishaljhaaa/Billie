from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.chatbot import RetrievalChatbot
from app.config import AppConfig, AuthConfig, LLMConfig
from app.memory import ConversationMemoryStore
from app.monitoring import AppMonitor
from app.schemas import ImageInput


RESULTS_DIR = PROJECT_ROOT / "artifacts"
DATASET_PATH = PROJECT_ROOT / "experiments" / "multimodal_benchmark_dataset.json"


def keyword_recall(answer: str, expected_keywords: list[str]) -> float:
    lowered = answer.lower()
    hits = sum(1 for keyword in expected_keywords if keyword.lower() in lowered)
    return hits / max(1, len(expected_keywords))


class EmptyVectorStore:
    def search(self, query: str, top_k: int):
        return []


def make_chatbot(session_store_path: Path) -> RetrievalChatbot:
    config = AppConfig(
        poll_interval_minutes=60,
        chunk_size=200,
        chunk_overlap=20,
        top_k=3,
        memory_window=4,
        vector_store_dir=PROJECT_ROOT / "data" / "multimodal_benchmark_store",
        metadata_db_path=PROJECT_ROOT / "data" / "multimodal_benchmark_state.db",
        session_store_path=session_store_path,
        source_timeout_seconds=5,
        source_max_retries=1,
        source_retry_backoff_seconds=0.0,
        llm=LLMConfig(api_key=None, model="unused", base_url="http://unused", timeout_seconds=5, max_retries=1),
        auth=AuthConfig(api_key=None, admin_key=None),
        sources=[],
    )
    return RetrievalChatbot(
        config,
        EmptyVectorStore(),
        AppMonitor(),
        None,
        memory_store=ConversationMemoryStore(session_store_path),
    )


def evaluate_variant(name: str, use_images: bool, rows: list[dict[str, object]]) -> dict[str, float | str]:
    session_store = PROJECT_ROOT / "data" / f"{name.lower()}_sessions.json"
    if session_store.exists():
        session_store.unlink()
    chatbot = make_chatbot(session_store)

    keyword_scores: list[float] = []
    clarification_hits = 0
    grounded_hits = 0

    for row in rows:
        image_inputs = [
            ImageInput(path=str(PROJECT_ROOT / path))
            for path in list(row["image_inputs"])
        ] if use_images else []
        response = chatbot.answer(
            str(row["question"]),
            session_id=str(row["session_id"]),
            image_inputs=image_inputs,
        )
        keyword_scores.append(keyword_recall(response.answer, list(row["expected_keywords"])))
        if response.needs_clarification == bool(row["expected_clarification"]):
            clarification_hits += 1
        if response.validation and response.validation.grounded:
            grounded_hits += 1

    total = len(rows)
    return {
        "model": name,
        "avg_keyword_recall": round(sum(keyword_scores) / total, 3),
        "clarification_accuracy": round(clarification_hits / total, 3),
        "grounded_rate": round(grounded_hits / total, 3),
    }


def save_bar_chart(title: str, results: list[dict[str, float | str]], metric: str, output_name: str) -> None:
    models = [str(item["model"]) for item in results]
    values = [float(item[metric]) for item in results]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(models, values, color=["#8A4F3D", "#2F7A72"])
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
    rows = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    results = [
        evaluate_variant("TextOnlyFallback", use_images=False, rows=rows),
        evaluate_variant("MultimodalReasoner", use_images=True, rows=rows),
    ]
    (RESULTS_DIR / "multimodal_benchmark_results.json").write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )
    save_bar_chart(
        "Multimodal Answer Keyword Recall",
        results,
        metric="avg_keyword_recall",
        output_name="multimodal_keyword_recall.png",
    )
    save_bar_chart(
        "Clarification Accuracy",
        results,
        metric="clarification_accuracy",
        output_name="multimodal_clarification_accuracy.png",
    )
    save_bar_chart(
        "Grounded Response Rate",
        results,
        metric="grounded_rate",
        output_name="multimodal_grounded_rate.png",
    )


if __name__ == "__main__":
    run()
