from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from app.schemas import EvidenceItem, ImageInput


class VisionClient(Protocol):
    def analyze_image(self, question: str, image_path: str, description: str | None = None) -> dict[str, Any]:
        ...


class VisualAnalyzer:
    def __init__(self, vision_client: VisionClient | None = None) -> None:
        self.vision_client = vision_client

    def analyze(self, question: str, image_inputs: list[ImageInput]) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        for image_input in image_inputs:
            image_path = Path(image_input.path)
            payload = self._load_sidecar(image_path)
            if payload is None and image_path.suffix.lower() == ".json":
                payload = json.loads(image_path.read_text(encoding="utf-8"))
            if payload is None and self.vision_client is not None:
                payload = self.vision_client.analyze_image(
                    question,
                    str(image_path),
                    image_input.description,
                )
            evidence.append(self._to_evidence(image_input, payload))
        return evidence

    def _load_sidecar(self, image_path: Path) -> dict[str, Any] | None:
        sidecar_path = image_path.with_suffix(".json")
        if not sidecar_path.exists():
            return None
        return json.loads(sidecar_path.read_text(encoding="utf-8"))

    def _to_evidence(self, image_input: ImageInput, payload: dict[str, Any] | None) -> EvidenceItem:
        if payload is None:
            summary = image_input.description or f"Image supplied at {image_input.path}, but no extractor was available."
            return EvidenceItem(
                modality="image",
                source=image_input.path,
                summary=summary,
                confidence=0.25,
                details=["Limited image understanding because no sidecar metadata or vision model was available."],
            )

        details = list(payload.get("evidence", []))
        entities = list(payload.get("entities", []))
        ambiguities = list(payload.get("ambiguities", []))
        if payload.get("ocr_text"):
            details.append(f"OCR: {payload['ocr_text']}")
        if entities:
            details.append(f"Entities: {', '.join(entities)}")
        details.extend(f"Ambiguity: {item}" for item in ambiguities)
        return EvidenceItem(
            modality="image",
            source=image_input.path,
            summary=str(payload.get("summary", image_input.description or image_input.path)),
            confidence=float(payload.get("confidence", 0.7)),
            details=details,
        )
