from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.multilingual import LanguageDetector

RESULTS_DIR = PROJECT_ROOT / "docs" / "evaluation" / "baseline-2026-09-26"

def run(results_dir: Path | None = None) -> dict[str, object]:
    rows = json.loads((PROJECT_ROOT / "dataset" / "multilingual_evaluation.json").read_text(encoding="utf-8"))
    detector = LanguageDetector()
    language_hits = 0
    normalized_hits = 0
    details = []
    for row in rows:
        result = detector.analyze(row["text"])
        language_ok = result.primary_language == row["language"]
        terms_ok = all(term in result.normalized_query.lower() for term in row["normalized_terms"])
        language_hits += language_ok
        normalized_hits += terms_ok
        details.append({"text": row["text"], "expected": row["language"], "predicted": result.primary_language, "language_ok": language_ok, "terms_ok": terms_ok})
    payload = {
        "samples": len(rows),
        "language_accuracy": round(language_hits / len(rows), 3),
        "cross_lingual_retrieval_term_recall": round(normalized_hits / len(rows), 3),
        "details": details,
        "note": "This evaluates deterministic language detection and retrieval-term normalization. Set MULTILINGUAL_TRANSLATION_BACKEND=nllb to use the optional open-source NLLB full-sentence translation backend.",
    }
    artifact_dir = results_dir or RESULTS_DIR
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "multilingual_evaluation_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the offline language normalization evaluation.")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    print(json.dumps(run(parser.parse_args().results_dir), indent=2))
