from __future__ import annotations

import json
import sys
import argparse
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


RESULTS_DIR = PROJECT_ROOT / "docs" / "evaluation" / "baseline-2026-09-26"
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


def evaluate_variant(
    name: str,
    use_images: bool,
    rows: list[dict[str, object]],
    output_dir: Path,
) -> dict[str, object]:
    session_dir = output_dir / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_store = session_dir / f"{name.lower()}_sessions.json"
    if session_store.exists():
        session_store.unlink()
    chatbot = make_chatbot(session_store)

    keyword_scores: list[float] = []
    clarification_hits = 0
    grounded_hits = 0
    per_query: list[dict[str, object]] = []
    missing_images: list[str] = []

    for row in rows:
        image_inputs = [
            ImageInput(path=str(PROJECT_ROOT / path))
            for path in list(row["image_inputs"])
        ] if use_images else []
        for image_input in image_inputs:
            if not Path(image_input.path).is_file():
                missing_images.append(image_input.path)
        response = chatbot.answer(
            str(row["question"]),
            session_id=str(row["session_id"]),
            image_inputs=image_inputs,
        )
        keyword_scores.append(keyword_recall(response.answer, list(row["expected_keywords"])))
        clarification_match = response.needs_clarification == bool(row["expected_clarification"])
        if clarification_match:
            clarification_hits += 1
        is_grounded = bool(response.validation and response.validation.grounded)
        if is_grounded:
            grounded_hits += 1
        per_query.append(
            {
                "id": row["id"],
                "question": row["question"],
                "expected_keywords": row["expected_keywords"],
                "keyword_recall": round(keyword_scores[-1], 3),
                "expected_clarification": bool(row["expected_clarification"]),
                "actual_clarification": response.needs_clarification,
                "clarification_match": clarification_match,
                "validator_grounded": is_grounded,
                "image_paths": [item.path for item in image_inputs],
                "all_images_present": all(Path(item.path).is_file() for item in image_inputs),
                "answer": response.answer,
            }
        )

    total = len(rows)
    return {
        "model": name,
        "avg_keyword_recall": round(sum(keyword_scores) / total, 3),
        "clarification_accuracy": round(clarification_hits / total, 3),
        "grounded_rate": round(grounded_hits / total, 3),
        "evaluation_status": "blocked_missing_image_assets" if missing_images else "completed_with_available_assets",
        "missing_image_paths": sorted(set(missing_images)),
        "per_query": per_query,
    }


def save_bar_chart(
    title: str,
    results: list[dict[str, object]],
    metric: str,
    output_name: str,
    output_dir: Path,
) -> None:
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
    plt.savefig(output_dir / output_name, dpi=180)
    plt.close()


def run(results_dir: Path | None = None) -> list[dict[str, object]]:
    output_dir = results_dir or RESULTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    results = [
        evaluate_variant("TextOnlyFallback", use_images=False, rows=rows, output_dir=output_dir),
        evaluate_variant("MultimodalReasoner", use_images=True, rows=rows, output_dir=output_dir),
    ]
    per_query = {str(result["model"]): result.pop("per_query") for result in results}
    (output_dir / "multimodal_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (output_dir / "multimodal_per_query.json").write_text(
        json.dumps(per_query, indent=2),
        encoding="utf-8",
    )
    save_bar_chart(
        "Multimodal Answer Keyword Recall",
        results,
        metric="avg_keyword_recall",
        output_name="multimodal_keyword_recall.png",
        output_dir=output_dir,
    )
    save_bar_chart(
        "Clarification Accuracy",
        results,
        metric="clarification_accuracy",
        output_name="multimodal_clarification_accuracy.png",
        output_dir=output_dir,
    )
    save_bar_chart(
        "Grounded Response Rate",
        results,
        metric="grounded_rate",
        output_name="multimodal_grounded_rate.png",
        output_dir=output_dir,
    )
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the multimodal fallback benchmark.")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    run(parser.parse_args().results_dir)
