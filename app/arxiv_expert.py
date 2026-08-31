from __future__ import annotations

import json
import math
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

from app.preprocessing import tokenize_and_lemmatize


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


@dataclass(frozen=True)
class ArxivPaper:
    paper_id: str
    title: str
    abstract: str
    authors: str
    categories: str
    published: str = ""


@dataclass(frozen=True)
class Concept:
    text: str
    score: float


@dataclass(frozen=True)
class ArxivAnswer:
    answer: str
    papers: list[ArxivPaper]
    concepts: list[Concept]
    follow_up_context: str
    used_local_llm: bool


class ArxivDatasetLoader:
    def load(self, dataset_path: Path, category_prefix: str = "cs.", limit: int = 5000) -> list[ArxivPaper]:
        if not dataset_path.exists():
            return []

        if dataset_path.is_dir():
            candidates = [
                dataset_path / "arxiv-metadata-oai-snapshot.json",
                dataset_path / "sample_arxiv_cs.jsonl",
            ]
            paths = [path for path in candidates if path.exists()]
            if not paths:
                paths = sorted(dataset_path.glob("*.jsonl")) + sorted(dataset_path.glob("*.json"))
        else:
            paths = [dataset_path]

        papers: list[ArxivPaper] = []
        for path in paths:
            papers.extend(self._load_file(path, category_prefix, limit - len(papers)))
            if len(papers) >= limit:
                break
        return papers

    def _load_file(self, path: Path, category_prefix: str, remaining: int) -> list[ArxivPaper]:
        papers: list[ArxivPaper] = []
        with path.open("r", encoding="utf-8") as handle:
            first = handle.read(1)
            handle.seek(0)
            if first == "[":
                rows = json.load(handle)
            else:
                rows = (json.loads(line) for line in handle if line.strip())

            for item in rows:
                categories = str(item.get("categories", ""))
                if category_prefix and not any(category.startswith(category_prefix) for category in categories.split()):
                    continue
                abstract = " ".join(str(item.get("abstract", "")).split())
                title = " ".join(str(item.get("title", "")).split())
                if not title or not abstract:
                    continue
                papers.append(
                    ArxivPaper(
                        paper_id=str(item.get("id", item.get("paper_id", ""))),
                        title=title,
                        abstract=abstract,
                        authors=str(item.get("authors", "")),
                        categories=categories,
                        published=str(item.get("update_date", item.get("published", ""))),
                    )
                )
                if len(papers) >= remaining:
                    break
        return papers


class ArxivRetriever:
    def __init__(self, papers: list[ArxivPaper]) -> None:
        self.papers = papers
        self._vectors = [self._vectorize(self._paper_text(paper)) for paper in papers]

    def search(self, query: str, top_k: int = 5) -> list[tuple[ArxivPaper, float]]:
        query_vector = self._vectorize(query)
        scored: list[tuple[ArxivPaper, float]] = []
        for paper, vector in zip(self.papers, self._vectors, strict=False):
            score = self._cosine(query_vector, vector)
            if score > 0:
                scored.append((paper, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    def _paper_text(self, paper: ArxivPaper) -> str:
        return f"{paper.title} {paper.abstract} {paper.categories}"

    def _vectorize(self, text: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for token in tokenize_and_lemmatize(text):
            if token in STOPWORDS:
                continue
            counts[token] = counts.get(token, 0) + 1
        return counts

    def _cosine(self, left: dict[str, int], right: dict[str, int]) -> float:
        overlap = set(left).intersection(right)
        numerator = sum(left[token] * right[token] for token in overlap)
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if not numerator or not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)


class ScientificNLP:
    def extract_concepts(self, text: str, top_k: int = 10) -> list[Concept]:
        candidates: dict[str, int] = {}
        normalized = re.sub(r"[^A-Za-z0-9\-\s]", " ", text)
        phrases = re.findall(
            r"\b(?:[A-Za-z][A-Za-z0-9\-]*\s+){1,4}(?:model|network|learning|attention|retrieval|transformer|embedding|optimization|classification|generation|inference|reasoning|algorithm|dataset|graph|vision)\b",
            normalized,
            flags=re.IGNORECASE,
        )
        for phrase in phrases:
            cleaned = " ".join(phrase.lower().split())
            candidates[cleaned] = candidates.get(cleaned, 0) + 3
        for token in tokenize_and_lemmatize(text):
            if token not in STOPWORDS and len(token) > 4:
                candidates[token] = candidates.get(token, 0) + 1

        total = max(1, max(candidates.values(), default=1))
        ranked = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
        return [Concept(text=term, score=round(count / total, 3)) for term, count in ranked[:top_k]]

    def summarize(self, paper: ArxivPaper, max_sentences: int = 3) -> str:
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", paper.abstract)
            if sentence.strip()
        ]
        if len(sentences) <= max_sentences:
            return paper.abstract

        title_tokens = set(tokenize_and_lemmatize(paper.title))
        scored: list[tuple[float, int, str]] = []
        for index, sentence in enumerate(sentences):
            sentence_tokens = set(tokenize_and_lemmatize(sentence))
            score = len(title_tokens.intersection(sentence_tokens)) + min(2, len(sentence_tokens) / 20)
            scored.append((score, index, sentence))
        selected = sorted(scored, key=lambda item: item[0], reverse=True)[:max_sentences]
        return " ".join(sentence for _, _, sentence in sorted(selected, key=lambda item: item[1]))

    def concept_graph_dot(self, concepts: list[Concept]) -> str:
        lines = ["graph concepts {", "  rankdir=LR;", "  node [shape=box, style=rounded];"]
        safe_names = []
        for index, concept in enumerate(concepts[:8]):
            node = f"c{index}"
            safe_names.append(node)
            label = concept.text.replace('"', "'")
            lines.append(f'  {node} [label="{label}"];')
        for left, right in zip(safe_names, safe_names[1:], strict=False):
            lines.append(f"  {left} -- {right};")
        lines.append("}")
        return "\n".join(lines)


class LocalOpenSourceLLM:
    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1")

    def explain(self, question: str, context: str) -> str:
        payload = {
            "model": self.model,
            "prompt": (
                "You are a computer science research assistant. Explain using only the paper context. "
                "Be clear, technical, and concise.\n\n"
                f"Question: {question}\n\nContext:\n{context}"
            ),
            "stream": False,
        }
        with httpx.Client(timeout=20) as client:
            response = client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
        return str(response.json().get("response", "")).strip()


class ArxivExpertService:
    def __init__(self, papers: list[ArxivPaper], llm: LocalOpenSourceLLM | None = None) -> None:
        self.papers = papers
        self.retriever = ArxivRetriever(papers)
        self.nlp = ScientificNLP()
        self.llm = llm

    @classmethod
    def from_dataset(cls, dataset_path: Path, fallback_sample_path: Path, use_local_llm: bool = False) -> "ArxivExpertService":
        loader = ArxivDatasetLoader()
        papers = loader.load(dataset_path, category_prefix="cs.")
        if not papers:
            papers = loader.load(fallback_sample_path, category_prefix="cs.")
        llm = LocalOpenSourceLLM() if use_local_llm else None
        return cls(papers, llm)

    def answer(self, question: str, history: list[str] | None = None) -> ArxivAnswer:
        history = history or []
        query = " ".join(history[-2:] + [question])
        matches = self.retriever.search(query, top_k=3)
        if not matches:
            return ArxivAnswer(
                answer="I could not find a relevant computer science paper in the indexed arXiv records.",
                papers=[],
                concepts=[],
                follow_up_context="",
                used_local_llm=False,
            )

        papers = [paper for paper, _ in matches]
        summaries = [f"{paper.title}: {self.nlp.summarize(paper)}" for paper in papers]
        context = "\n\n".join(summaries)
        concepts = self.nlp.extract_concepts(context)

        if self.llm is not None:
            try:
                explanation = self.llm.explain(question, context)
                if explanation:
                    return ArxivAnswer(
                        answer=explanation,
                        papers=papers,
                        concepts=concepts,
                        follow_up_context=context,
                        used_local_llm=True,
                    )
            except Exception:
                pass

        answer = (
            f"Most relevant paper: {papers[0].title}\n\n"
            f"Summary: {self.nlp.summarize(papers[0])}\n\n"
            f"Key concepts: {', '.join(concept.text for concept in concepts[:5])}."
        )
        return ArxivAnswer(
            answer=answer,
            papers=papers,
            concepts=concepts,
            follow_up_context=context,
            used_local_llm=False,
        )

    def to_dict(self, answer: ArxivAnswer) -> dict[str, Any]:
        payload = asdict(answer)
        payload["papers"] = [asdict(paper) for paper in answer.papers]
        payload["concepts"] = [asdict(concept) for concept in answer.concepts]
        return payload
