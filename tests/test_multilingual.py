from __future__ import annotations

from app.multilingual import LanguageDetector, MultilingualResponseAdapter


def test_language_detector_supports_three_additional_languages():
    detector = LanguageDetector()

    spanish = detector.analyze("Como actualiza la base de conocimiento?")
    hindi = detector.analyze("ज्ञान बेस कैसे अपडेट होता है?")
    bengali = detector.analyze("জ্ঞান বেস কিভাবে আপডেট হয়?")

    assert spanish.primary_language == "es"
    assert "update" in spanish.normalized_query
    assert hindi.primary_language == "hi"
    assert "knowledge" in hindi.normalized_query
    assert bengali.primary_language == "bn"
    assert "knowledge" in bengali.normalized_query


def test_language_detector_handles_mixed_language_input():
    result = LanguageDetector().analyze("Please actualiza ज्ञान base")

    assert result.mixed_language is True
    assert "update" in result.normalized_query
    assert "knowledge" in result.normalized_query


def test_english_shared_vocabulary_is_not_misclassified_as_spanish():
    result = LanguageDetector().analyze("Where should I report phishing?")

    assert result.primary_language == "en"


def test_multilingual_response_adapter_marks_response_language():
    language = LanguageDetector().analyze("Como actualiza la base de conocimiento?")
    answer = MultilingualResponseAdapter().adapt("The knowledge base updates on a schedule.", language)

    assert answer.startswith("Respuesta en espanol:")
