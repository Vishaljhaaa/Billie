from __future__ import annotations

from pathlib import Path

from app.medical_qa import MedicalEntityRecognizer, MedicalQARecord, MedicalQAService, MedQuADParser


def test_medquad_parser_reads_xml_records(tmp_path: Path):
    xml_path = tmp_path / "record.xml"
    xml_path.write_text(
        """
        <Document>
          <Focus>Asthma</Focus>
          <CUI>C0004096</CUI>
          <SemanticType>Disease or Syndrome</SemanticType>
          <QAPairs>
            <QAPair qtype="symptoms">
              <Question>What are symptoms of asthma?</Question>
              <Answer>Asthma may cause coughing, wheezing, and shortness of breath.</Answer>
            </QAPair>
          </QAPairs>
        </Document>
        """.strip(),
        encoding="utf-8",
    )

    records = MedQuADParser().load(tmp_path)

    assert len(records) == 1
    assert records[0].focus == "Asthma"
    assert records[0].question_type == "symptoms"
    assert "shortness of breath" in records[0].answer


def test_medical_entities_use_sentence_case_and_keep_existing_categories():
    entities = MedicalEntityRecognizer().extract(
        "asthma may cause fever and shortness of breath; treatment may include surgery."
    )

    assert ("Asthma", "disease") in {(entity.text, entity.category) for entity in entities}
    assert ("Fever", "symptom") in {(entity.text, entity.category) for entity in entities}
    assert ("Shortness of breath", "symptom") in {(entity.text, entity.category) for entity in entities}
    assert ("Surgery", "treatment") in {(entity.text, entity.category) for entity in entities}


def test_medical_entities_deduplicate_case_insensitively_and_preserve_focus():
    record = MedicalQARecord(
        question="What is asthma?",
        answer="Asthma is a disease.",
        source="sample.json",
        focus="ASTHMA",
        semantic_type="Disease or Syndrome",
    )

    entities = MedicalEntityRecognizer().extract("asthma and ASTHMA", record)
    asthma_entities = [
        entity for entity in entities
        if entity.category == "disease" and entity.text.casefold() == "asthma"
    ]

    assert len(asthma_entities) == 1
    assert asthma_entities[0].text == "ASTHMA"

    canonical_focus = MedicalQARecord(
        question="What is the condition?",
        answer="The condition is described in the record.",
        source="sample.json",
        focus="Type 2 Diabetes",
        entity_category="disease",
    )
    focus_entities = MedicalEntityRecognizer().extract("condition", canonical_focus)

    assert any(entity.text == "Type 2 Diabetes" and entity.category == "disease" for entity in focus_entities)


def test_medical_qa_retrieves_answer_and_entities():
    service = MedicalQAService.from_dataset(
        Path("dataset/does-not-exist"),
        fallback_sample_path=Path("dataset/medquad_sample/sample_medquad_records.json"),
    )

    result = service.answer("What symptoms happen with asthma?")

    assert "airways" in result.answer.lower() or "wheezing" in result.answer.lower()
    assert result.score > 0
    assert any(entity.category == "disease" and entity.text == "Asthma" for entity in result.entities)
    assert any(entity.category == "symptom" for entity in result.entities)
    assert "not a diagnosis" in result.disclaimer


def test_medical_qa_reports_when_no_dataset_records_are_available():
    result = MedicalQAService([]).answer("What symptoms happen with asthma?")

    assert result.score == 0.0
    assert result.source == ""
    assert "could not find a relevant answer" in result.answer.lower()
