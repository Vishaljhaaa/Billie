from __future__ import annotations

import json
from pathlib import Path

from experiments.run_benchmark import run
from experiments.run_multimodal_benchmark import run as run_multimodal


def test_benchmark_generates_results(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VECTOR_STORE_BACKEND", "local")
    run(tmp_path)

    results_path = tmp_path / "retrieval_results.json"
    assert results_path.exists()

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    assert len(payload) == 2
    assert {row["model"] for row in payload} == {"KeywordOverlap", "CosineOverlap"}
    per_query = json.loads((tmp_path / "retrieval_per_query.json").read_text(encoding="utf-8"))
    assert len(per_query["KeywordOverlap"]) == 5


def test_multimodal_benchmark_generates_isolated_results(tmp_path: Path):
    run_multimodal(tmp_path)

    results_path = tmp_path / "multimodal_results.json"
    assert results_path.exists()

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    assert len(payload) == 2
    assert {row["model"] for row in payload} == {"TextOnlyFallback", "MultimodalReasoner"}
    assert payload[1]["evaluation_status"] == "blocked_missing_image_assets"
    assert (tmp_path / "multimodal_per_query.json").exists()
