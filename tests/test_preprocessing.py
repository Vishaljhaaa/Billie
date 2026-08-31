from __future__ import annotations

import app.preprocessing as preprocessing


def test_tokenize_and_lemmatize_uses_word_forms(monkeypatch):
    class FakeLemmatizer:
        def lemmatize(self, token: str) -> str:
            mapping = {
                "symptoms": "symptom",
                "diseases": "disease",
                "treatments": "treatment",
            }
            return mapping.get(token, token)

    monkeypatch.setattr(preprocessing, "_wordnet_lemmatizer", lambda: FakeLemmatizer())

    tokens = preprocessing.tokenize_and_lemmatize("Symptoms of diseases and treatments")

    assert tokens == ["symptom", "of", "disease", "and", "treatment"]
