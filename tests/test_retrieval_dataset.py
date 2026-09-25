from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = PROJECT_ROOT / "experiments" / "datasets" / "retrieval-v1"


def load_dataset():
    metadata = json.loads((DATASET_DIR / "metadata.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (DATASET_DIR / "queries.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return metadata, rows


def test_retrieval_v1_labels_reference_frozen_source_text():
    metadata, rows = load_dataset()
    sources = {source["source_id"]: source for source in metadata["sources"]}
    source_text = {
        source_id: " ".join((PROJECT_ROOT / source["path"]).read_text(encoding="utf-8").split())
        for source_id, source in sources.items()
    }

    for source_id, source in sources.items():
        content = (PROJECT_ROOT / source["path"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == source["sha256"]
        assert len(content) == source["bytes"]

    assert len(rows) == metadata["counts"]["queries"]
    assert len({row["query_id"] for row in rows}) == len(rows)
    assert {row["query_type"] for row in rows} >= {
        "exact_keyword", "paraphrase", "multi_source", "ambiguous_multi_passage", "unanswerable_missing_number"
    }

    for row in rows:
        if row["answerability"] == "unanswerable":
            assert row["relevant_passages"] == []
            assert row["unanswerable_reason"]
            continue

        assert row["relevant_passages"]
        for passage in row["relevant_passages"]:
            assert passage["source_id"] in sources
            assert passage["quote"] in source_text[passage["source_id"]]
            assert passage["relevance"] in {1, 2}


def test_retrieval_v1_splits_keep_evidence_clusters_together():
    metadata, rows = load_dataset()
    split_by_cluster: dict[str, str] = {}
    for row in rows:
        cluster = row["evidence_cluster"]
        previous_split = split_by_cluster.setdefault(cluster, row["split"])
        assert previous_split == row["split"]

    assert Counter(row["answerability"] for row in rows) == {
        "answerable": metadata["counts"]["answerable"],
        "unanswerable": metadata["counts"]["unanswerable"],
    }
    assert Counter(row["split"] for row in rows) == {
        "development": metadata["counts"]["development"],
        "test": metadata["counts"]["test"],
    }
