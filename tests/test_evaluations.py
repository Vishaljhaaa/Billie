import json
from pathlib import Path

from experiments.run_multilingual_evaluation import run as run_multilingual_evaluation
from experiments.run_sentiment_evaluation import run as run_sentiment_evaluation


def test_sentiment_evaluation_writes_accuracy_and_appropriateness_results():
    result = run_sentiment_evaluation()

    assert result["accuracy"] >= 0.8
    assert result["macro_f1"] >= 0.8
    assert result["response_appropriateness_rate"] == 1.0
    assert Path("artifacts/sentiment_evaluation_results.json").exists()


def test_multilingual_evaluation_writes_cross_lingual_results():
    result = run_multilingual_evaluation()

    assert result["language_accuracy"] >= 0.875
    assert result["cross_lingual_retrieval_term_recall"] >= 0.875
    payload = json.loads(Path("artifacts/multilingual_evaluation_results.json").read_text(encoding="utf-8"))
    assert payload["samples"] == 8
