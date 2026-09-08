from __future__ import annotations

import re
from typing import Any

from app.document_ai.contracts import ReviewTask, ValidationResult
from app.document_ai.models import CanonicalDocument

LOW_CONFIDENCE = 0.70


def validate_document(document: CanonicalDocument) -> tuple[list[ValidationResult], list[ReviewTask]]:
    results: list[ValidationResult] = []
    review_tasks: list[ReviewTask] = []
    results.extend(_validate_evidence(document))
    results.extend(_validate_tables(document))
    results.extend(_validate_financial_consistency(document))
    for entity_index, entity in enumerate(document.entities, start=1):
        confidence = entity.confidence.value if entity.confidence else 0.0
        if confidence < LOW_CONFIDENCE or not entity.evidence:
            priority = "high" if entity.entity_type in {"MONEY", "INVOICE_NUMBER"} else "normal"
            review_tasks.append(
                ReviewTask(
                    task_id=f"review-entity-{entity_index}",
                    field=entity.entity_type,
                    value=entity.raw_value,
                    priority=priority,
                    confidence=confidence,
                    reason="low_confidence" if confidence < LOW_CONFIDENCE else "missing_evidence",
                    evidence=[item.to_dict() for item in entity.evidence],
                )
            )
    return results, review_tasks


def _validate_evidence(document: CanonicalDocument) -> list[ValidationResult]:
    important = [*document.all_blocks, *[cell for table in document.all_tables for row in table.rows for cell in row]]
    covered = sum(1 for item in important if getattr(item, "evidence", None))
    coverage = covered / max(1, len(important))
    status = "valid" if coverage >= 0.95 else "uncertain" if coverage >= 0.70 else "invalid"
    document.quality_dimensions.evidence_coverage = round(coverage, 4)
    return [ValidationResult("evidence_coverage", status, f"{covered}/{len(important)} extracted objects have evidence.")]


def _validate_tables(document: CanonicalDocument) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for table in document.all_tables:
        widths = [len(row) for row in table.rows]
        consistent = len(set(widths)) <= 1 if widths else True
        status = "valid" if consistent else "uncertain"
        results.append(ValidationResult("table_column_consistency", status, f"Table {table.table_id or 'unknown'} has row widths {widths}."))
    return results


def _validate_financial_consistency(document: CanonicalDocument) -> list[ValidationResult]:
    money = [entity for entity in document.entities if entity.entity_type == "MONEY" and isinstance(entity.normalized_value, (int, float))]
    if len(money) < 2:
        return [ValidationResult("invoice_arithmetic", "uncertain", "Not enough monetary evidence for arithmetic validation.")]
    values = [float(entity.normalized_value) for entity in money]
    largest = max(values)
    smaller = [value for value in values if value != largest]
    if not smaller:
        return [ValidationResult("invoice_arithmetic", "uncertain", "Only one distinct monetary value was found.")]
    plausible = any(abs(sum(smaller) - largest) <= max(1.0, largest * 0.01) for _ in [0])
    return [ValidationResult("invoice_arithmetic", "valid" if plausible else "uncertain", "Monetary values are internally plausible." if plausible else "Monetary values require review; no source value was changed.")]


def infer_field_status(value: Any, confidence: float | None, evidence: list[Any]) -> str:
    if value in (None, ""):
        return "not_found"
    if confidence is None or confidence < LOW_CONFIDENCE:
        return "uncertain"
    if not evidence:
        return "uncertain"
    return "valid"
