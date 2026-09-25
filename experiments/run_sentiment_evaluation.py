from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.sentiment import SentimentAnalyzer, SentimentResponseAdapter

RESULTS_DIR = PROJECT_ROOT / "docs" / "evaluation" / "baseline-2026-09-26"

def run(results_dir: Path | None = None) -> dict[str, object]:
    rows = json.loads((PROJECT_ROOT / "dataset" / "sentiment_evaluation.json").read_text(encoding="utf-8"))
    analyzer = SentimentAnalyzer()
    adapter = SentimentResponseAdapter()
    labels = ["positive", "negative", "neutral"]
    predictions = [analyzer.analyze(row["text"]).label for row in rows]
    expected = [row["label"] for row in rows]

    per_label: dict[str, dict[str, float]] = {}
    for label in labels:
        tp = sum(pred == label and truth == label for pred, truth in zip(predictions, expected, strict=False))
        fp = sum(pred == label and truth != label for pred, truth in zip(predictions, expected, strict=False))
        fn = sum(pred != label and truth == label for pred, truth in zip(predictions, expected, strict=False))
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        per_label[label] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(2 * precision * recall / max(0.000001, precision + recall), 3),
        }

    appropriate = 0
    for row in rows:
        sentiment = analyzer.analyze(row["text"])
        response = adapter.adapt("Evidence-based answer.", sentiment)
        if (sentiment.label == "negative" and response.startswith("I understand")) or (
            sentiment.label == "positive" and response.startswith("Glad this is helping")
        ) or (sentiment.label == "neutral" and response == "Evidence-based answer."):
            appropriate += 1

    payload: dict[str, object] = {
        "samples": len(rows),
        "accuracy": round(sum(pred == truth for pred, truth in zip(predictions, expected, strict=False)) / len(rows), 3),
        "macro_f1": round(sum(metric["f1"] for metric in per_label.values()) / len(labels), 3),
        "per_label": per_label,
        "response_appropriateness_rate": round(appropriate / len(rows), 3),
        "assessment": "Appropriateness checks whether negative messages receive empathy, positive messages receive acknowledgement, and neutral messages stay factual. This is a deterministic offline measure, not a real customer-satisfaction study.",
    }
    artifact_dir = results_dir or RESULTS_DIR
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "sentiment_evaluation_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    plt.figure(figsize=(7, 4))
    plt.bar(["Accuracy", "Macro F1", "Response appropriateness"], [payload["accuracy"], payload["macro_f1"], payload["response_appropriateness_rate"]], color="#2F7A72")
    plt.ylim(0, 1.05)
    plt.tight_layout()
    plt.savefig(artifact_dir / "sentiment_evaluation.png", dpi=180)
    plt.close()
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the offline sentiment evaluation.")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    print(json.dumps(run(parser.parse_args().results_dir), indent=2))
