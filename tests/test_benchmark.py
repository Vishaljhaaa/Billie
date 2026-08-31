from __future__ import annotations

import json
from pathlib import Path

from experiments.run_benchmark import run
from experiments.run_multimodal_benchmark import run as run_multimodal


def test_benchmark_generates_results(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VECTOR_STORE_BACKEND", "local")
    run()

    results_path = Path("artifacts/benchmark_results.json")
    assert results_path.exists()

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    assert len(payload) == 2
    assert {row["model"] for row in payload} == {"KeywordOverlap", "CosineOverlap"}


def test_multimodal_benchmark_generates_results():
    run_multimodal()

    results_path = Path("artifacts/multimodal_benchmark_results.json")
    assert results_path.exists()

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    assert len(payload) == 2
    assert {row["model"] for row in payload} == {"TextOnlyFallback", "MultimodalReasoner"}
