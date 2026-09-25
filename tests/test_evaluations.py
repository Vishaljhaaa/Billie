import json
from pathlib import Path

from experiments.run_multilingual_evaluation import run as run_multilingual_evaluation
from experiments.run_sentiment_evaluation import run as run_sentiment_evaluation


def test_sentiment_evaluation_writes_accuracy_and_appropriateness_results(tmp_path: Path):
    output_dir = tmp_path / "nested" / "sentiment"
    result = run_sentiment_evaluation(output_dir)

    assert result["accuracy"] >= 0.8
    assert result["macro_f1"] >= 0.8
    assert result["response_appropriateness_rate"] == 1.0
    assert (output_dir / "sentiment_evaluation_results.json").exists()


def test_multilingual_evaluation_writes_cross_lingual_results(tmp_path: Path):
    output_dir = tmp_path / "nested" / "multilingual"
    result = run_multilingual_evaluation(output_dir)

    assert result["language_accuracy"] >= 0.875
    assert result["cross_lingual_retrieval_term_recall"] >= 0.875
    payload = json.loads((output_dir / "multilingual_evaluation_results.json").read_text(encoding="utf-8"))
    assert payload["samples"] == 8
