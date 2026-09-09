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

KVP_PATTERNS: tuple[tuple[str, str], ...] = (
    ("Invoice_Number", r"(?i)(?:invoice\s*(?:no|number|#)?|inv\.?|ho[aó]\s*đơn\s*(?:số|so)?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9./-]{2,})"),
    ("Date", r"(?i)(?:invoice\s*date|date|ngày|ngay)\s*[:#-]?\s*(\d{1,4}[/-]\d{1,2}[/-]\d{1,4})"),
    ("Tax_Code", r"(?i)(?:tax\s*(?:code|id)|mst|mã\s*số\s*thuế|ma\s*so\s*thue)\s*[:#-]?\s*([0-9 -]{8,20})"),
    ("VAT_Rate", r"(?i)(?:vat|tax|thuế|thue)\s*(?:rate|%)?\s*[:#-]?\s*(\d{1,2}(?:[.,]\d+)?)\s*%"),
    ("Subtotal", r"(?i)(?:subtotal|sub-total|tạm\s*tính|tam\s*tinh)\s*[:#-]?\s*([^\n|]+)"),
    ("Grand_Total", r"(?i)(?:grand\s*total|total\s*due|total|tổng\s*cộng|tong\s*cong|tổng\s*tiền|tong\s*tien)\s*[:#-]?\s*([^\n|]+)"),
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
            for entity in _extract_kvps_from_block(block.text, page.page_number, block.bbox, block.block_id, document_id, block.confidence):
                key = (entity.entity_type, entity.raw_value, page.page_number)
                if key not in seen:
                    seen.add(key)
                    entities.append(entity)
    return entities


def _extract_kvps_from_block(text: str, page_number: int, bbox: Any, block_id: str | None, document_id: str, block_confidence: Confidence | None) -> list[DocumentEntity]:
    entities: list[DocumentEntity] = []
    for entity_type, pattern in KVP_PATTERNS:
        match = re.search(pattern, text)
        if not match:
            continue
        raw_value = match.group(1).strip(" :;,.\t")
        if entity_type == "Tax_Code":
            raw_value = re.sub(r"\D", "", raw_value)
        confidence = block_confidence or Confidence.from_score(0.86, "invoice-kvp-regex")
        evidence = Evidence(document_id, page_number, bbox, block_id=block_id, quote=text[:500], engine="invoice-kvp-regex", confidence=confidence.value)
        entities.append(DocumentEntity(entity_type, raw_value, _normalize(entity_type, raw_value), confidence, [evidence]))
    return entities


def _normalize(entity_type: str, value: str) -> Any:
    if entity_type in {"MONEY", "Subtotal", "Grand_Total"}:
        return parse_financial_number(value)
    if entity_type in {"PERCENT", "VAT_Rate"}:
        try:
            return float(value.replace("%", "").replace(",", ".").strip()) / 100
        except ValueError:
            return value
    if entity_type in {"DATE", "Date"}:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
    return value.strip()


def parse_financial_number(value: str) -> float | None:
    """Parse Vietnamese and international money formats without external services."""
    raw = re.sub(r"(?i)(vnđ|vnd|đ|usd|eur|gbp|[$€£₫])", "", value).strip()
    raw = re.sub(r"[^0-9,.-]", "", raw)
    if not raw:
        return None
    if "," in raw and "." in raw:
        decimal_separator = "." if raw.rfind(".") > raw.rfind(",") else ","
        thousands = "," if decimal_separator == "." else "."
        raw = raw.replace(thousands, "").replace(decimal_separator, ".")
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    elif raw.count(",") > 1:
        raw = raw.replace(",", "")
    elif "," in raw:
        left, right = raw.rsplit(",", 1)
        raw = raw.replace(",", ".") if len(right) <= 2 else raw.replace(",", "")
    elif "." in raw:
        left, right = raw.rsplit(".", 1)
        if len(right) == 3 and left.isdigit():
            raw = raw.replace(".", "")
    try:
        return float(raw)
    except ValueError:
        return None
