from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.document_ai.models import CanonicalDocument, Confidence, DocumentEntity, Evidence


PATTERNS: tuple[tuple[str, str], ...] = (
    ("EMAIL", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    ("URL", r"https?://[^\s]+"),
    ("INVOICE_NUMBER", r"(?i)\b(?:invoice|inv|hoá đơn|hoa don)\s*(?:no|number|#|:)?\s*([A-Z0-9][A-Z0-9/-]{2,})"),
    ("PHONE", r"(?<!\d)(?:\+?\d[\d ()-]{7,}\d)(?!\d)"),
    ("DATE", r"\b\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b"),
    ("PERCENT", r"\b\d+(?:[.,]\d+)?\s?%"),
    ("MONEY", r"(?<!\w)(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{1,2})?\s?(?:VND|VNĐ|VNn|VNN|USD|EUR|GBP|₫|\$|€|£)\b"),
)


def extract_entities(document: CanonicalDocument) -> list[DocumentEntity]:
    entities: list[DocumentEntity] = []
    seen: set[tuple[str, str, int]] = set()
    document_id = document.source.fingerprint if document.source and document.source.fingerprint else document.source_filename
    for page in document.pages:
        for block in page.blocks:
            for entity_type, pattern in PATTERNS:
                for match in re.finditer(pattern, block.text):
                    raw_value = match.group(1) if entity_type == "INVOICE_NUMBER" and match.lastindex else match.group(0)
                    key = (entity_type, raw_value, page.page_number)
                    if key in seen:
                        continue
                    seen.add(key)
                    confidence = block.confidence or Confidence.from_score(0.72, "semantic-regex")
                    evidence = Evidence(document_id, page.page_number, block.bbox, block_id=block.block_id, quote=block.text, engine="semantic-regex", confidence=confidence.value)
                    entities.append(DocumentEntity(entity_type, raw_value, _normalize(entity_type, raw_value), confidence, [evidence]))
    return entities


def _normalize(entity_type: str, value: str) -> Any:
    if entity_type == "MONEY":
        number = re.sub(r"[^0-9,.-]", "", value)
        if number.count(",") and number.count("."):
            number = number.replace(".", "").replace(",", ".")
        elif number.count(".") > 1 or (number.count(".") == 1 and len(number.rsplit(".", 1)[-1]) == 3):
            number = number.replace(".", "")
        elif number.count(",") > 1 or (number.count(",") == 1 and len(number.rsplit(",", 1)[-1]) == 3):
            number = number.replace(",", "")
        else:
            number = number.replace(",", ".")
        try:
            return float(number)
        except ValueError:
            return value
    if entity_type == "PERCENT":
        try:
            return float(value.replace("%", "").replace(",", ".").strip()) / 100
        except ValueError:
            return value
    if entity_type == "DATE":
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
    return value.strip()
