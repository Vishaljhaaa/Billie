from __future__ import annotations

import re

from app.schemas import EvidenceItem, ValidationResult


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
    "how",
    "i",
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
    "what",
    "when",
    "where",
    "which",
    "with",
}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9@.\-]+", text.lower())
        if token not in STOPWORDS and len(token) > 1
    }


class ResponseValidator:
    def validate(
        self,
        *,
        answer: str,
        question: str,
        text_snippets: list[str],
        evidence: list[EvidenceItem],
        needs_clarification: bool,
    ) -> ValidationResult:
        issues: list[str] = []
        corpus = " ".join(text_snippets + [item.summary for item in evidence] + [detail for item in evidence for detail in item.details])
        corpus_tokens = _tokens(corpus)
        answer_tokens = _tokens(answer)
        question_tokens = _tokens(question)

        if not corpus_tokens:
            issues.append("No supporting evidence was available for validation.")

        supported = {
            token for token in answer_tokens if token in corpus_tokens or token in question_tokens
        }
        support_ratio = len(supported) / max(1, len(answer_tokens))
        # A clarification is deliberately a question to the user, not a factual
        # claim that must overlap with source text.
        if not needs_clarification and len(answer_tokens) >= 6 and support_ratio < 0.35:
            issues.append("The answer may contain unsupported claims beyond the retrieved evidence.")

        ambiguity_present = any("ambiguity:" in detail.lower() for item in evidence for detail in item.details)
        if ambiguity_present and not needs_clarification and "uncertain" not in answer.lower():
            issues.append("The visual evidence contains ambiguity that was not surfaced clearly.")

        grounded = not issues
        confidence = 0.92 if grounded else 0.55
        return ValidationResult(grounded=grounded, confidence=confidence, issues=issues)
