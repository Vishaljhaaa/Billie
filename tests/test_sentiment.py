from __future__ import annotations

from app.sentiment import SentimentAnalyzer, SentimentResponseAdapter


def test_sentiment_analyzer_detects_negative_positive_and_neutral():
    analyzer = SentimentAnalyzer()

    negative = analyzer.analyze("I am frustrated because this problem is terrible")
    positive = analyzer.analyze("Thanks, this is great and very helpful")
    neutral = analyzer.analyze("How does the chatbot update its source index?")

    assert negative.label == "negative"
    assert "frustrated" in negative.negative_hits
    assert positive.label == "positive"
    assert "great" in positive.positive_hits
    assert neutral.label == "neutral"


def test_sentiment_response_adapter_changes_tone():
    analyzer = SentimentAnalyzer()
    adapter = SentimentResponseAdapter()

    adapted = adapter.adapt(
        "Here is the answer.",
        analyzer.analyze("I am upset and confused"),
    )

    assert adapted.startswith("I understand this is frustrating.")
