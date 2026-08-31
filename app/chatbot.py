from __future__ import annotations

import re

from app.config import AppConfig
from app.llm import LLMClient
from app.memory import ConversationMemoryStore
from app.monitoring import AppMonitor
from app.multilingual import LanguageDetector, LanguageResult, MultilingualResponseAdapter, NLLBTranslator
from app.reasoning import ReasoningEngine
from app.schemas import ChatResponse, EvidenceItem, ImageInput, LanguagePayload, SentimentPayload
from app.sentiment import SentimentAnalyzer, SentimentResponseAdapter
from app.validation import ResponseValidator
from app.vector_store import VectorStore
from app.vision import VisualAnalyzer


# Terms such as "how" and "what" occur in nearly every web page and must not
# make an unrelated document appear relevant to a user question.
RETRIEVAL_STOPWORDS = {
    "a", "an", "and", "are", "can", "do", "does", "for", "from", "how",
    "i", "in", "is", "it", "me", "of", "on", "please", "should", "the",
    "this", "to", "what", "when", "where", "which", "who", "with", "you",
}

# Simple greeting phrases to handle chit-chat without hitting the retrieval layer.
GREETING_PATTERNS = (
    r"^\s*(hi|hello|hey|greetings)([\s!.,]*)$",
    r"^\s*(good\s+morning|good\s+afternoon|good\s+evening)([\s!.,]*)$",
)


class RetrievalChatbot:
    def __init__(
        self,
        config: AppConfig,
        vector_store: VectorStore,
        monitor: AppMonitor,
        llm_client: LLMClient | None = None,
        memory_store: ConversationMemoryStore | None = None,
        visual_analyzer: VisualAnalyzer | None = None,
        validator: ResponseValidator | None = None,
        reasoning_engine: ReasoningEngine | None = None,
        sentiment_analyzer: SentimentAnalyzer | None = None,
        sentiment_adapter: SentimentResponseAdapter | None = None,
        language_detector: LanguageDetector | None = None,
        language_adapter: MultilingualResponseAdapter | None = None,
    ) -> None:
        self.config = config
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.monitor = monitor
        self.memory_store = memory_store or ConversationMemoryStore(config.session_store_path)
        self.visual_analyzer = visual_analyzer or VisualAnalyzer(llm_client)
        self.validator = validator or ResponseValidator()
        self.reasoning_engine = reasoning_engine or ReasoningEngine()
        self.sentiment_analyzer = sentiment_analyzer or SentimentAnalyzer()
        self.sentiment_adapter = sentiment_adapter or SentimentResponseAdapter()
        translator = NLLBTranslator.from_environment()
        self.language_detector = language_detector or LanguageDetector(translator)
        self.language_adapter = language_adapter or MultilingualResponseAdapter(translator)

    def answer(
        self,
        question: str,
        session_id: str = "default",
        image_inputs: list[ImageInput] | None = None,
    ) -> ChatResponse:
        self.monitor.record_chat()
        language = self.language_detector.analyze(question)
        self.monitor.record_language(language.primary_language)
        sentiment = self.sentiment_analyzer.analyze(question)
        self.monitor.record_sentiment(sentiment.label)
        # Short-circuit simple greetings with a friendly, contextual reply.
        lowered = question.strip().lower()
        for patt in GREETING_PATTERNS:
            if re.match(patt, lowered):
                greeting_answer = (
                    "Hello — I'm the Unified AI Chatbot. Ask me about the knowledge base "
                    "(company handbook, product updates, security playbook), or type a specific question."
                )
                adapted = self.sentiment_adapter.adapt(greeting_answer, sentiment)
                adapted = self.language_adapter.adapt(adapted, language)
                return ChatResponse(
                    answer=adapted,
                    sources=[],
                    used_llm=False,
                    session_id=session_id,
                    sentiment=self._sentiment_payload(sentiment),
                    language=self._language_payload(language),
                    validation=self.validator.validate(
                        answer=adapted,
                        question=question,
                        text_snippets=[],
                        evidence=[],
                        needs_clarification=False,
                    ),
                )
        if image_inputs:
            self.monitor.record_image_chat(len(image_inputs))
        matches = self.vector_store.search(language.normalized_query, top_k=self.config.top_k)
        # Image-backed queries keep their retrieved context for cross-checking;
        # text-only questions must pass the relevance guard.
        if not image_inputs:
            matches = [
                match for match in matches
                if "_score" not in match
                or self._has_meaningful_overlap(language.normalized_query, match["content"])
                or float(match["_score"]) >= 0.35
            ]
        snippets = [match["content"] for match in matches]
        text_evidence = [
            EvidenceItem(
                modality="text",
                source=match["metadata"]["location"],
                summary=match["content"],
                confidence=0.78,
            )
            for match in matches
        ]
        visual_evidence = self.visual_analyzer.analyze(question, image_inputs or [])
        memory_turns = self.memory_store.recent_turns(session_id, self.config.memory_window)
        all_evidence = text_evidence + visual_evidence
        sources = list(
            dict.fromkeys(
                [match["metadata"]["location"] for match in matches]
                + [item.source for item in visual_evidence]
            )
        )

        if not all_evidence and not memory_turns:
            answer = self.sentiment_adapter.adapt(
                "I couldn't find relevant text or visual evidence in the current knowledge base.",
                sentiment,
            )
            answer = self.language_adapter.adapt(answer, language)
            return ChatResponse(
                answer=answer,
                sources=[],
                used_llm=False,
                session_id=session_id,
                sentiment=self._sentiment_payload(sentiment),
                language=self._language_payload(language),
                validation=self.validator.validate(
                    answer=answer,
                    question=question,
                    text_snippets=[],
                    evidence=[],
                    needs_clarification=False,
                ),
            )

        needs_clarification, follow_up_question = self.reasoning_engine.detect_ambiguity(
            question=question,
            evidence=visual_evidence,
        )
        if needs_clarification:
            self.monitor.record_clarification()

        if self.llm_client is not None:
            try:
                answer = self.llm_client.answer_multimodal(
                    question,
                    text_contexts=snippets,
                    visual_contexts=self._format_visual_contexts(visual_evidence),
                    conversation_context=memory_turns,
                )
                self.monitor.record_llm_success()
                validation = self.validator.validate(
                    answer=answer,
                    question=question,
                    text_snippets=snippets,
                    evidence=visual_evidence,
                    needs_clarification=needs_clarification,
                )
                if not validation.grounded:
                    answer = self._compose_fallback_answer(
                        question,
                        snippets,
                        visual_evidence,
                        memory_turns,
                        needs_clarification,
                        follow_up_question,
                    )
                answer = self.sentiment_adapter.adapt(answer, sentiment)
                answer = self.language_adapter.adapt(answer, language)
                self.memory_store.append_turn(
                    session_id,
                    question=question,
                    answer=answer,
                    sources=sources,
                    visual_summaries=[item.summary for item in visual_evidence],
                )
                return ChatResponse(
                    answer=answer,
                    sources=sources,
                    used_llm=True,
                    session_id=session_id,
                    sentiment=self._sentiment_payload(sentiment),
                    language=self._language_payload(language),
                    evidence=all_evidence,
                    needs_clarification=needs_clarification,
                    follow_up_question=follow_up_question,
                    validation=validation,
                )
            except Exception:
                self.monitor.record_llm_failure()

        answer = self._compose_fallback_answer(
            question,
            snippets,
            visual_evidence,
            memory_turns,
            needs_clarification,
            follow_up_question,
        )
        answer = self.sentiment_adapter.adapt(answer, sentiment)
        answer = self.language_adapter.adapt(answer, language)
        validation = self.validator.validate(
            answer=answer,
            question=question,
            text_snippets=snippets,
            evidence=visual_evidence,
            needs_clarification=needs_clarification,
        )
        self.memory_store.append_turn(
            session_id,
            question=question,
            answer=answer,
            sources=sources,
            visual_summaries=[item.summary for item in visual_evidence],
        )
        return ChatResponse(
            answer=answer,
            sources=sources,
            used_llm=False,
            session_id=session_id,
            sentiment=self._sentiment_payload(sentiment),
            language=self._language_payload(language),
            evidence=all_evidence,
            needs_clarification=needs_clarification,
            follow_up_question=follow_up_question,
            validation=validation,
        )

    def _compose_fallback_answer(
        self,
        question: str,
        snippets: list[str],
        visual_evidence: list[EvidenceItem],
        memory_turns: list[dict[str, str]],
        needs_clarification: bool,
        follow_up_question: str | None,
    ) -> str:
        return self._synthesize_direct_answer(
            question,
            snippets,
            visual_evidence,
            memory_turns,
            needs_clarification,
            follow_up_question,
        )

    def _format_visual_contexts(self, evidence: list[EvidenceItem]) -> list[str]:
        return [
            "\n".join([item.summary, *item.details]).strip()
            for item in evidence
        ]

    def _synthesize_direct_answer(
        self,
        question: str,
        snippets: list[str],
        visual_evidence: list[EvidenceItem],
        memory_turns: list[dict[str, str]],
        needs_clarification: bool,
        follow_up_question: str | None,
    ) -> str:
        corpus = " ".join(
            snippets
            + [item.summary for item in visual_evidence]
            + [detail for item in visual_evidence for detail in item.details]
            + [turn.get("answer", "") for turn in memory_turns]
        )
        if needs_clarification and follow_up_question:
            return f"The available evidence is ambiguous. {follow_up_question}"

        lowered_question = question.lower()
        email_match = re.search(r"[\w.\-]+@[\w.\-]+\.\w+", corpus)
        date_match = re.search(
            r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}",
            corpus,
            flags=re.IGNORECASE,
        )

        if ("email" in lowered_question or "report" in lowered_question or "where" in lowered_question) and email_match:
            return f"Based on the evidence, report it to {email_match.group(0)}."
        if "phishing" in lowered_question or "report" in lowered_question:
            return "I could not find a confirmed phishing-reporting channel in the indexed sources."
        if "when" in lowered_question and date_match:
            return f"Based on the evidence, the relevant date is {date_match.group(0)}."
        if "repeat" in lowered_question and email_match:
            return f"The reporting email in the recent evidence is {email_match.group(0)}."

        if visual_evidence:
            return visual_evidence[0].summary
        if snippets:
            return snippets[0]
        return "I could not confirm an answer from the available evidence."

    def _sentiment_payload(self, sentiment) -> SentimentPayload:
        return SentimentPayload(
            label=sentiment.label,
            score=sentiment.score,
            positive_hits=sentiment.positive_hits,
            negative_hits=sentiment.negative_hits,
        )

    def _has_meaningful_overlap(self, question: str, content: str) -> bool:
        question_terms = {
            self._normalize_retrieval_term(token) for token in re.findall(r"[a-z0-9]{3,}", question.lower())
            if token not in RETRIEVAL_STOPWORDS
        }
        if not question_terms:
            return False
        content_terms = {
            self._normalize_retrieval_term(token) for token in re.findall(r"[a-z0-9]{3,}", content.lower())
        }
        return bool(question_terms.intersection(content_terms))

    def _normalize_retrieval_term(self, token: str) -> str:
        if token.endswith("ies") and len(token) > 4:
            return token[:-3] + "y"
        if token.endswith("s") and len(token) > 3:
            return token[:-1]
        return token

    def _language_payload(self, language: LanguageResult) -> LanguagePayload:
        return LanguagePayload(
            primary_language=language.primary_language,
            language_name=language.language_name,
            detected_languages=language.detected_languages,
            mixed_language=language.mixed_language,
            confidence=language.confidence,
            normalized_query=language.normalized_query,
            ambiguous=language.ambiguous,
            notes=language.notes,
        )
