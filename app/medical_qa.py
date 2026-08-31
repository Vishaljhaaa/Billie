from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.preprocessing import tokenize_and_lemmatize


@dataclass(frozen=True)
class MedicalQARecord:
    question: str
    answer: str
    source: str
    question_type: str = ""
    focus: str = ""
    cui: str = ""
    semantic_type: str = ""
    entity_category: str = ""
    synonyms: tuple[str, ...] = ()


@dataclass(frozen=True)
class MedicalEntity:
    text: str
    category: str


@dataclass(frozen=True)
class MedicalQAResult:
    answer: str
    source: str
    score: float
    matched_question: str
    entities: list[MedicalEntity]
    question_type: str
    focus: str
    disclaimer: str


MEDICAL_DISCLAIMER = (
    "This is educational information from the indexed medical QA dataset, not a diagnosis "
    "or a substitute for professional medical care."
)


SYMPTOM_TERMS = {
    "ache",
    "bleeding",
    "bruising",
    "cough",
    "dizziness",
    "fatigue",
    "fever",
    "headache",
    "nausea",
    "pain",
    "rash",
    "shortness of breath",
    "sweating",
    "swelling",
    "vomiting",
    "weakness",
    "weight loss",
}

TREATMENT_TERMS = {
    "antibiotic",
    "biologic therapy",
    "chemotherapy",
    "drug",
    "immunotherapy",
    "medicine",
    "radiation therapy",
    "stem cell transplant",
    "surgery",
    "targeted therapy",
    "therapy",
    "treatment",
}

DISEASE_HINTS = {
    "anemia",
    "asthma",
    "cancer",
    "diabetes",
    "disease",
    "disorder",
    "infection",
    "leukemia",
    "syndrome",
}


class MedQuADParser:
    def load(self, dataset_dir: Path) -> list[MedicalQARecord]:
        if not dataset_dir.exists():
            return []

        records: list[MedicalQARecord] = []
        for xml_path in sorted(dataset_dir.rglob("*.xml")):
            records.extend(self._parse_xml(xml_path))
        for json_path in sorted(dataset_dir.rglob("*.json")):
            if json_path.name.startswith("sample_medquad"):
                records.extend(self._parse_json(json_path))
        return records

    def _parse_xml(self, xml_path: Path) -> list[MedicalQARecord]:
        root = ET.parse(xml_path).getroot()
        records: list[MedicalQARecord] = []
        fallback_focus = self._first_text(root, {"focus", "Focus", "name", "Name"})
        fallback_cui = self._first_text(root, {"cui", "CUI"})
        fallback_semantic = self._first_text(root, {"semanticType", "SemanticType", "semantic_type"})

        for qa_node in root.iter():
            if self._clean_tag(qa_node.tag).lower() not in {"qa", "qapair", "questionanswerpair"}:
                continue
            question = self._child_text(qa_node, {"question", "Question"})
            answer = self._child_text(qa_node, {"answer", "Answer"})
            if not question or not answer:
                continue
            records.append(
                MedicalQARecord(
                    question=question,
                    answer=answer,
                    source=str(xml_path),
                    question_type=self._metadata_value(qa_node, {"qtype", "type", "question_type", "QuestionType"}),
                    focus=self._metadata_value(qa_node, {"focus", "Focus"}) or fallback_focus,
                    cui=self._metadata_value(qa_node, {"cui", "CUI"}) or fallback_cui,
                    semantic_type=self._metadata_value(qa_node, {"semanticType", "SemanticType", "semantic_type"}) or fallback_semantic,
                    entity_category=self._metadata_value(qa_node, {"category", "Category"}),
                    synonyms=tuple(self._metadata_list(qa_node, {"synonym", "Synonym", "synonyms", "Synonyms"})),
                )
            )

        if records:
            return records

        question_nodes = [
            node for node in root.iter() if self._clean_tag(node.tag).lower() == "question"
        ]
        for question_node in question_nodes:
            answer = self._sibling_or_child_text(question_node, {"answer", "Answer"})
            question = (question_node.text or "").strip()
            if question and answer:
                records.append(
                    MedicalQARecord(
                        question=question,
                        answer=answer,
                        source=str(xml_path),
                        question_type=question_node.attrib.get("qtype", question_node.attrib.get("type", "")),
                        focus=fallback_focus,
                        cui=fallback_cui,
                        semantic_type=fallback_semantic,
                    )
                )
        return records

    def _parse_json(self, json_path: Path) -> list[MedicalQARecord]:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        return [
            MedicalQARecord(
                question=str(item["question"]),
                answer=str(item["answer"]),
                source=str(json_path),
                question_type=str(item.get("question_type", "")),
                focus=str(item.get("focus", "")),
                cui=str(item.get("cui", "")),
                semantic_type=str(item.get("semantic_type", "")),
                entity_category=str(item.get("entity_category", "")),
                synonyms=tuple(item.get("synonyms", [])),
            )
            for item in payload
        ]

    def _clean_tag(self, tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    def _child_text(self, node: ET.Element, names: set[str]) -> str:
        wanted = {name.lower() for name in names}
        for child in node:
            if self._clean_tag(child.tag).lower() in wanted:
                return " ".join("".join(child.itertext()).split())
        return ""

    def _first_text(self, node: ET.Element, names: set[str]) -> str:
        wanted = {name.lower() for name in names}
        for child in node.iter():
            if self._clean_tag(child.tag).lower() in wanted:
                return " ".join("".join(child.itertext()).split())
        return ""

    def _metadata_value(self, node: ET.Element, names: set[str]) -> str:
        for name in names:
            if name in node.attrib:
                return node.attrib[name].strip()
        return self._child_text(node, names)

    def _metadata_list(self, node: ET.Element, names: set[str]) -> list[str]:
        wanted = {name.lower() for name in names}
        values: list[str] = []
        for child in node.iter():
            if self._clean_tag(child.tag).lower() in wanted:
                text = " ".join("".join(child.itertext()).split())
                if text:
                    values.extend(part.strip() for part in text.split("|") if part.strip())
        return values

    def _sibling_or_child_text(self, node: ET.Element, names: set[str]) -> str:
        answer = self._child_text(node, names)
        if answer:
            return answer
        parent = self._parent_map.get(node)
        if parent is None:
            return ""
        return self._child_text(parent, names)

    @property
    def _parent_map(self) -> dict[ET.Element, ET.Element]:
        return {}


class MedicalEntityRecognizer:
    def extract(self, text: str, record: MedicalQARecord | None = None) -> list[MedicalEntity]:
        entities: list[MedicalEntity] = []
        lowered = text.lower()

        for term in sorted(SYMPTOM_TERMS, key=len, reverse=True):
            if term in lowered:
                entities.append(MedicalEntity(text=term, category="symptom"))
        for term in sorted(TREATMENT_TERMS, key=len, reverse=True):
            if term in lowered:
                entities.append(MedicalEntity(text=term, category="treatment"))
        for term in sorted(DISEASE_HINTS, key=len, reverse=True):
            if term in lowered:
                entities.append(MedicalEntity(text=term, category="disease"))

        if record is not None and record.focus:
            category = record.entity_category.lower() or self._category_from_semantic_type(record.semantic_type)
            entities.append(MedicalEntity(text=record.focus, category=category or "medical_focus"))

        deduped: dict[tuple[str, str], MedicalEntity] = {}
        for entity in entities:
            deduped[(entity.text.lower(), entity.category)] = entity
        return list(deduped.values())

    def _category_from_semantic_type(self, semantic_type: str) -> str:
        lowered = semantic_type.lower()
        if "disorder" in lowered or "disease" in lowered:
            return "disease"
        if "drug" in lowered or "chemical" in lowered:
            return "treatment"
        return ""


class MedicalQARetriever:
    def __init__(self, records: list[MedicalQARecord]) -> None:
        self.records = records
        self._record_vectors = [self._vectorize(self._record_text(record)) for record in records]

    def search(self, query: str, top_k: int = 3) -> list[tuple[MedicalQARecord, float]]:
        query_vector = self._vectorize(query)
        query_type = self._infer_question_type(query)
        scored: list[tuple[MedicalQARecord, float]] = []
        for record, record_vector in zip(self.records, self._record_vectors, strict=False):
            score = self._cosine(query_vector, record_vector)
            if query_type and query_type in record.question_type.lower():
                score += 0.15
            if score > 0:
                scored.append((record, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    def _record_text(self, record: MedicalQARecord) -> str:
        return " ".join(
            [
                record.question,
                record.answer[:500],
                record.question_type,
                record.focus,
                record.semantic_type,
                " ".join(record.synonyms),
            ]
        )

    def _infer_question_type(self, query: str) -> str:
        lowered = query.lower()
        if any(term in lowered for term in ["symptom", "sign", "feel", "happen"]):
            return "symptom"
        if any(term in lowered for term in ["treat", "therapy", "medicine", "drug"]):
            return "treatment"
        if any(term in lowered for term in ["diagnose", "test", "detect"]):
            return "diagnosis"
        return ""

    def _vectorize(self, text: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for token in tokenize_and_lemmatize(text):
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


class MedicalQAService:
    def __init__(self, records: list[MedicalQARecord]) -> None:
        self.records = records
        self.retriever = MedicalQARetriever(records)
        self.entity_recognizer = MedicalEntityRecognizer()

    @classmethod
    def from_dataset(cls, dataset_dir: Path, fallback_sample_path: Path | None = None) -> "MedicalQAService":
        parser = MedQuADParser()
        records = parser.load(dataset_dir)
        if not records and fallback_sample_path is not None:
            records = parser.load(fallback_sample_path.parent)
        return cls(records)

    def answer(self, question: str) -> MedicalQAResult:
        matches = self.retriever.search(question, top_k=1)
        question_entities = self.entity_recognizer.extract(question)
        if not matches:
            return MedicalQAResult(
                answer="I could not find a relevant answer in the indexed MedQuAD records.",
                source="",
                score=0.0,
                matched_question="",
                entities=question_entities,
                question_type="",
                focus="",
                disclaimer=MEDICAL_DISCLAIMER,
            )

        record, score = matches[0]
        entities = self.entity_recognizer.extract(f"{question} {record.answer}", record)
        return MedicalQAResult(
            answer=record.answer,
            source=record.source,
            score=round(score, 3),
            matched_question=record.question,
            entities=entities,
            question_type=record.question_type,
            focus=record.focus,
            disclaimer=MEDICAL_DISCLAIMER,
        )

    def to_dict(self, result: MedicalQAResult) -> dict[str, Any]:
        payload = asdict(result)
        payload["entities"] = [asdict(entity) for entity in result.entities]
        return payload
