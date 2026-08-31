from __future__ import annotations

from app.schemas import EvidenceItem


class ReasoningEngine:
    def detect_ambiguity(
        self,
        *,
        question: str,
        evidence: list[EvidenceItem],
    ) -> tuple[bool, str | None]:
        lowered_question = question.lower()
        question_tokens = set(lowered_question.replace("?", " ").split())
        ambiguity_messages = [
            detail.removeprefix("Ambiguity: ").strip()
            for item in evidence
            for detail in item.details
            if detail.lower().startswith("ambiguity:")
        ]
        if not ambiguity_messages:
            return False, None

        entity_tokens = {
            token.lower()
            for item in evidence
            for detail in item.details
            if detail.startswith("Entities:")
            for token in detail.split(":", 1)[1].replace(",", " ").split()
        }
        mentions_entity = bool(entity_tokens.intersection(question_tokens))
        generic_question = any(
            phrase in lowered_question
            for phrase in ["what date", "when does it start", "what launch date", "what time"]
        )
        if generic_question and not mentions_entity:
            return True, "Which item in the image would you like me to focus on?"

        return True, "The image may support more than one interpretation, so I am answering cautiously."
