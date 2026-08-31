from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "hi": "Hindi",
    "bn": "Bengali",
}


LANGUAGE_MARKERS = {
    "es": {
        "actualiza": "update",
        "actualizar": "update",
        "conocimiento": "knowledge",
        "correo": "email",
        "donde": "where",
        "gracias": "thanks",
        "informe": "report",
        "informo": "report",
        "pregunta": "question",
        "seguridad": "security",
        "sincroniza": "sync",
    },
    "hi": {
        "अपडेट": "update",
        "ज्ञान": "knowledge",
        "बेस": "base",
        "सुरक्षा": "security",
        "कहां": "where",
        "कहाँ": "where",
        "कैसे": "how",
        "रिपोर्ट": "report",
        "करें": "do",
        "ईमेल": "email",
        "सिंक": "sync",
        "धन्यवाद": "thanks",
    },
    "bn": {
        "আপডেট": "update",
        "জ্ঞান": "knowledge",
        "বেস": "base",
        "নিরাপত্তা": "security",
        "কোথায়": "where",
        "কিভাবে": "how",
        "রিপোর্ট": "report",
        "ইমেল": "email",
        "সিঙ্ক": "sync",
        "ধন্যবাদ": "thanks",
    },
}


LANGUAGE_OPENERS = {
    "en": "",
    "es": "Respuesta en espanol: ",
    "hi": "हिंदी उत्तर: ",
    "bn": "বাংলা উত্তর: ",
}


@dataclass(frozen=True)
class LanguageResult:
    primary_language: str
    language_name: str
    detected_languages: list[str]
    mixed_language: bool
    confidence: float
    normalized_query: str
    ambiguous: bool
    notes: list[str]


class TranslationClient(Protocol):
    def translate(self, text: str, source_language: str, target_language: str) -> str:
        ...


class NLLBTranslator:
    """Optional local translation backend using Meta's open-source NLLB model.

    The model is loaded only when ``MULTILINGUAL_TRANSLATION_BACKEND=nllb`` is
    configured. This keeps the default demo lightweight while allowing real
    full-sentence cross-lingual retrieval and response generation.
    """

    MODEL_NAME = "facebook/nllb-200-distilled-600M"
    LANGUAGE_CODES = {"en": "eng_Latn", "es": "spa_Latn", "hi": "hin_Deva", "bn": "ben_Beng"}

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or self.MODEL_NAME
        self._tokenizer = None
        self._model = None

    @classmethod
    def from_environment(cls) -> "NLLBTranslator | None":
        import os

        if os.getenv("MULTILINGUAL_TRANSLATION_BACKEND", "lexicon").lower() != "nllb":
            return None
        return cls(os.getenv("NLLB_MODEL", cls.MODEL_NAME))

    def _load(self) -> None:
        if self._tokenizer is not None:
            return
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "NLLB translation needs transformers, torch, and sentencepiece. "
                "Install the optional multilingual dependencies first."
            ) from exc
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)

    def translate(self, text: str, source_language: str, target_language: str) -> str:
        if source_language == target_language:
            return text
        if source_language not in self.LANGUAGE_CODES or target_language not in self.LANGUAGE_CODES:
            return text
        self._load()
        assert self._tokenizer is not None and self._model is not None
        self._tokenizer.src_lang = self.LANGUAGE_CODES[source_language]
        encoded = self._tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        generated = self._model.generate(
            **encoded,
            forced_bos_token_id=self._tokenizer.lang_code_to_id[self.LANGUAGE_CODES[target_language]],
            max_new_tokens=256,
        )
        return self._tokenizer.batch_decode(generated, skip_special_tokens=True)[0]


class LanguageDetector:
    def __init__(self, translator: TranslationClient | None = None) -> None:
        self.translator = translator

    def analyze(self, text: str) -> LanguageResult:
        scores = {"en": 0, "es": 0, "hi": 0, "bn": 0}
        notes: list[str] = []

        if re.search(r"[\u0900-\u097F]", text):
            scores["hi"] += 3
            notes.append("Detected Devanagari script.")
        if re.search(r"[\u0980-\u09FF]", text):
            scores["bn"] += 3
            notes.append("Detected Bengali script.")

        lowered = text.lower()
        ascii_tokens = re.findall(r"[a-záéíóúñü]+", lowered)
        if ascii_tokens:
            scores["en"] += 1
        for language, lexicon in LANGUAGE_MARKERS.items():
            for marker in lexicon:
                if re.search(rf"\b{re.escape(marker.lower())}\b", lowered):
                    scores[language] += 2

        detected = [language for language, score in scores.items() if score > 0]
        if not detected:
            detected = ["en"]
            scores["en"] = 1

        primary = max(scores, key=scores.get)
        if scores[primary] == 0:
            primary = "en"

        mixed = len([language for language in detected if language != "en" or scores[language] > 1]) > 1
        top_score = scores[primary]
        total_score = max(1, sum(scores.values()))
        confidence = round(min(1.0, top_score / total_score + 0.25), 3)
        ambiguous = confidence < 0.55 or (mixed and top_score <= 2)
        if mixed:
            notes.append("Mixed-language input detected.")
        if ambiguous:
            notes.append("Language intent is ambiguous; preserving the strongest detected language.")

        normalized_query = self.normalize_query(text)
        if self.translator is not None and primary != "en":
            try:
                normalized_query = self.translator.translate(text, primary, "en")
                notes.append("Full-sentence query translated to English with the NLLB open-source model.")
            except Exception as exc:
                notes.append(f"NLLB translation unavailable; used deterministic term normalization ({exc}).")

        return LanguageResult(
            primary_language=primary,
            language_name=SUPPORTED_LANGUAGES[primary],
            detected_languages=detected,
            mixed_language=mixed,
            confidence=confidence,
            normalized_query=normalized_query,
            ambiguous=ambiguous,
            notes=notes,
        )

    def normalize_query(self, text: str) -> str:
        normalized = text
        for lexicon in LANGUAGE_MARKERS.values():
            for source, target in lexicon.items():
                normalized = re.sub(re.escape(source), target, normalized, flags=re.IGNORECASE)
        return normalized


class MultilingualResponseAdapter:
    def __init__(self, translator: TranslationClient | None = None) -> None:
        self.translator = translator

    def adapt(self, answer: str, language: LanguageResult) -> str:
        if self.translator is not None and language.primary_language != "en":
            try:
                return self.translator.translate(answer, "en", language.primary_language)
            except Exception:
                pass
        opener = LANGUAGE_OPENERS.get(language.primary_language, "")
        if not opener or answer.startswith(opener):
            return answer
        return opener + answer
