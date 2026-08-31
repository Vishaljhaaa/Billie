from __future__ import annotations

import re
from dataclasses import dataclass

from app.preprocessing import tokenize_and_lemmatize


POSITIVE_WORDS = {
    "awesome",
    "excellent",
    "good",
    "great",
    "happy",
    "helpful",
    "love",
    "perfect",
    "pleased",
    "satisfied",
    "thanks",
    "thank",
    "wonderful",
}

NEGATIVE_WORDS = {
    "angry",
    "awful",
    "bad",
    "broken",
    "confused",
    "disappointed",
    "frustrated",
    "hate",
    "issue",
    "mad",
    "problem",
    "terrible",
    "upset",
    "worried",
    "wrong",
}

NEGATION_WORDS = {"not", "never", "no", "cannot", "can't", "dont", "don't", "isnt", "isn't"}


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: float
    positive_hits: list[str]
    negative_hits: list[str]


class SentimentAnalyzer:
    def analyze(self, text: str) -> SentimentResult:
        tokens = tokenize_and_lemmatize(text)
        positive_hits: list[str] = []
        negative_hits: list[str] = []

        for index, token in enumerate(tokens):
            negated = self._is_negated(tokens, index)
            if token in POSITIVE_WORDS:
                if negated:
                    negative_hits.append(f"not {token}")
                else:
                    positive_hits.append(token)
            if token in NEGATIVE_WORDS:
                if negated:
                    positive_hits.append(f"not {token}")
                else:
                    negative_hits.append(token)

        exclamation_boost = min(2, text.count("!"))
        raw_score = len(positive_hits) - len(negative_hits)
        if raw_score > 0:
            raw_score += exclamation_boost * 0.25
        elif raw_score < 0:
            raw_score -= exclamation_boost * 0.25

        if raw_score >= 1:
            label = "positive"
        elif raw_score <= -1:
            label = "negative"
        else:
            label = "neutral"

        confidence = min(1.0, abs(raw_score) / 3)
        if label == "neutral":
            confidence = 0.5 if positive_hits or negative_hits else 0.35

        return SentimentResult(
            label=label,
            score=round(confidence, 3),
            positive_hits=positive_hits,
            negative_hits=negative_hits,
        )

    def _is_negated(self, tokens: list[str], index: int) -> bool:
        window = tokens[max(0, index - 3) : index]
        return any(token in NEGATION_WORDS for token in window)


class SentimentResponseAdapter:
    def adapt(self, answer: str, sentiment: SentimentResult) -> str:
        if sentiment.label == "negative":
            prefix = "I understand this is frustrating. "
            if answer.startswith(prefix):
                return answer
            return prefix + answer
        if sentiment.label == "positive":
            prefix = "Glad this is helping. "
            if answer.startswith(prefix):
                return answer
            return prefix + answer
        return answer


def clean_customer_text(text: str) -> str:
    return " ".join(re.sub(r"\s+", " ", text).split())
