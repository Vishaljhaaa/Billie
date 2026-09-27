from __future__ import annotations

from pathlib import Path

from app.config import AppConfig
from app.retrieval import BM25Retriever, RetrievalChunk
from app.vector_store import VectorStore


def chunk(chunk_id: str, content: str) -> RetrievalChunk:
    return RetrievalChunk(chunk_id=chunk_id, content=content, metadata={"source_id": "fixture"})


def test_bm25_scores_hand_computable_single_term_case():
    retriever = BM25Retriever(
        [chunk("a", "rare"), chunk("b", "common common")],
        k1=1.2,
        b=0.75,
    )

    # N=2, df(rare)=1, avgdl=1.5, dl=1, tf=1, so IDF=ln(2).
    length_norm = 1.0 - 0.75 + 0.75 * 1.0 / 1.5
    expected = __import__("math").log(2.0) * (1.2 + 1.0) / (1.0 + 1.2 * length_norm)
    assert abs(retriever.score_document(["rare"], 0) - expected) < 1e-12
    assert retriever.search("rare", top_k=1)[0].chunk.chunk_id == "a"


def test_bm25_returns_empty_for_empty_and_missing_queries():
    retriever = BM25Retriever([chunk("only", "security policy")])

    assert retriever.search("!!!", top_k=4) == []
    assert retriever.search("astronomy", top_k=4) == []
    assert retriever.search("security", top_k=0) == []
    assert BM25Retriever([]).search("security", top_k=4) == []


def test_bm25_repeated_terms_and_punctuation_are_deterministic():
    retriever = BM25Retriever(
        [chunk("a", "API-key: key"), chunk("b", "API credential")]
    )

    once = retriever.search("api-key", top_k=2)
    repeated = retriever.search("api-key api-key", top_k=2)

    assert [item.chunk.chunk_id for item in once] == ["a", "b"]
    assert [item.chunk.chunk_id for item in repeated] == ["a", "b"]
    assert repeated[0].score == 2 * once[0].score


def test_bm25_document_length_normalization_and_tie_breaking():
    retriever = BM25Retriever(
        [
            chunk("z-long", "signal filler filler filler filler"),
            chunk("b-short", "signal"),
            chunk("a-short", "signal"),
        ]
    )

    results = retriever.search("signal", top_k=3)

    assert [item.chunk.chunk_id for item in results] == ["a-short", "b-short", "z-long"]
    assert results[0].score == results[1].score > results[2].score


def test_vector_store_uses_bm25_when_retrieval_mode_is_selected(tmp_path: Path):
    config = AppConfig(
        poll_interval_minutes=60,
        chunk_size=100,
        chunk_overlap=10,
        top_k=3,
        memory_window=4,
        vector_store_dir=tmp_path / "chroma",
        metadata_db_path=tmp_path / "state.db",
        session_store_path=tmp_path / "sessions.json",
        source_timeout_seconds=5,
        source_max_retries=2,
        source_retry_backoff_seconds=0.0,
        llm=None,
        auth=None,
        sources=[],
        retrieval_mode="bm25",
        bm25_k1=1.2,
        bm25_b=0.75,
        rrf_k=60,
    )
    vector_store = VectorStore(config)
    vector_store.replace_source_chunks("doc", ["rare", "rare common"], "fixture.txt")

    results = vector_store.search("rare", top_k=2)

    assert [item["content"] for item in results] == ["rare", "rare common"]
    assert results[0]["_score"] >= results[1]["_score"]
