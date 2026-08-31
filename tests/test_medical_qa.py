from __future__ import annotations

from pathlib import Path

from app.medical_qa import MedicalQAService, MedQuADParser


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
