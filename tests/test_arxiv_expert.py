from __future__ import annotations

from pathlib import Path

from app.arxiv_expert import ArxivDatasetLoader, ArxivExpertService, ScientificNLP


def test_arxiv_loader_filters_computer_science_sample():
    papers = ArxivDatasetLoader().load(
        Path("dataset/arxiv_sample/sample_arxiv_cs.jsonl"),
        category_prefix="cs.",
    )

    assert len(papers) >= 3
    assert all("cs." in paper.categories for paper in papers)


def test_arxiv_expert_retrieves_rag_and_extracts_concepts():
    service = ArxivExpertService.from_dataset(
        Path("dataset/arxiv/missing.json"),
        fallback_sample_path=Path("dataset/arxiv_sample/sample_arxiv_cs.jsonl"),
        use_local_llm=False,
    )

    answer = service.answer("How does retrieval augmented generation help question answering?")

    assert answer.papers
    assert "retrieval" in answer.papers[0].title.lower()
    assert any("retrieval" in concept.text for concept in answer.concepts)
    assert answer.follow_up_context
    assert answer.used_local_llm is False


def test_scientific_nlp_builds_concept_graph():
    concepts = ScientificNLP().extract_concepts(
        "Transformer attention model improves retrieval augmented generation for question answering.",
        top_k=5,
    )
    graph = ScientificNLP().concept_graph_dot(concepts)

    assert concepts
    assert graph.startswith("graph concepts")


def test_arxiv_expert_reports_when_no_dataset_records_are_available():
    answer = ArxivExpertService([]).answer("How does retrieval augmented generation work?")

    assert answer.papers == []
    assert "could not find a relevant computer science paper" in answer.answer.lower()
