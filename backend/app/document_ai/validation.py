from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.document_ai.contracts import ReviewTask, TruthStatus, ValidationResult
from app.document_ai.models import CanonicalDocument, DocumentCell, DocumentTable

LOW_CONFIDENCE = 0.70
_TOLERANCE = Decimal("0.01")


def validate_document(document: CanonicalDocument) -> tuple[list[ValidationResult], list[ReviewTask]]:
    results: list[ValidationResult] = []
    review_tasks: list[ReviewTask] = []
    results.extend(_validate_evidence(document))
    results.extend(_validate_tables(document))
    arithmetic_results, arithmetic_tasks = _validate_financial_consistency(document)
    results.extend(arithmetic_results)
    review_tasks.extend(arithmetic_tasks)
    for entity_index, entity in enumerate(document.entities, start=1):
        confidence = entity.confidence.value if entity.confidence else 0.0
        if confidence < LOW_CONFIDENCE or not entity.evidence:
            priority = "high" if entity.entity_type in {"MONEY", "INVOICE_NUMBER"} else "normal"
            review_tasks.append(ReviewTask(task_id=f"review-entity-{entity_index}", field=entity.entity_type, value=entity.raw_value, priority=priority, confidence=confidence, reason="low_confidence" if confidence < LOW_CONFIDENCE else "missing_evidence", evidence=[item.to_dict() for item in entity.evidence]))
    if any(item.reason == "arithmetic_conflict" for item in review_tasks):
        for fact in document.facts:
            fact.status = TruthStatus.CONFLICTING
            fact.explanation.append("arithmetic validation produced a conflicting table relationship")
    return results, review_tasks


def _validate_evidence(document: CanonicalDocument) -> list[ValidationResult]:
    important = [*document.all_blocks, *[cell for table in document.all_tables for row in table.rows for cell in row]]
    covered = sum(1 for item in important if getattr(item, "evidence", None))
    coverage = covered / max(1, len(important))
    document.quality_dimensions.evidence_coverage = round(coverage, 4)
    status = "valid" if coverage >= 0.95 else "uncertain" if coverage >= 0.70 else "invalid"
    return [ValidationResult("evidence_coverage", status, f"{covered}/{len(important)} extracted objects have evidence.")]


def _validate_tables(document: CanonicalDocument) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for table in document.all_tables:
        widths = [len(row) for row in table.rows]
        consistent = len(set(widths)) <= 1 if widths else True
        results.append(ValidationResult("table_column_consistency", "valid" if consistent else "uncertain", f"Table {table.table_id or 'unknown'} has row widths {widths}."))
    return results


def _money(value: str) -> Decimal | None:
    compact = re.sub(r"[^0-9,.-]", "", value.replace(" ", ""))
    if not compact or not re.fullmatch(r"[-+]?\d[\d.,]*", compact):
        return None
    if "," in compact and "." in compact:
        decimal_separator = "." if compact.rfind(".") > compact.rfind(",") else ","
        thousands = "," if decimal_separator == "." else "."
        compact = compact.replace(thousands, "").replace(decimal_separator, ".")
    elif compact.count(".") > 1:
        compact = compact.replace(".", "")
    elif compact.count(",") > 1:
        compact = compact.replace(",", "")
    else:
        compact = compact.replace(",", ".")
    try:
        return Decimal(compact)
    except InvalidOperation:
        return None


def _header_index(headers: list[str], names: set[str]) -> int | None:
    for index, header in enumerate(headers):
        normalized = re.sub(r"[^a-z0-9]", "", header.casefold())
        if any(alias in normalized for alias in names):
            return index
    return None


def _conflict_task(table: DocumentTable, row_number: int, cell: DocumentCell, field: str, message: str) -> ReviewTask:
    return ReviewTask(task_id=f"review-conflict-{table.table_id or table.page_number}-{row_number}-{field}", field=f"{table.table_id or 'table'}:{field}", value=cell.text, priority="high", confidence=cell.confidence.value if cell.confidence else 0.0, reason="arithmetic_conflict", evidence=[item.to_dict() for item in cell.evidence] + [{"page": table.page_number, "table_id": table.table_id, "quote": message}])


def _validate_financial_consistency(document: CanonicalDocument) -> tuple[list[ValidationResult], list[ReviewTask]]:
    results: list[ValidationResult] = []
    tasks: list[ReviewTask] = []
    for table in document.all_tables:
        if len(table.rows) < 2:
            continue
        headers = [cell.text for cell in table.rows[0]]
        qty = _header_index(headers, {"qty", "quantity", "soluong"})
        unit = _header_index(headers, {"unitprice", "price", "dongia"})
        total = _header_index(headers, {"linetotal", "total", "amount", "thanhtien"})
        if qty is not None and unit is not None and total is not None:
            checks = 0
            failures = 0
            for row_number, row in enumerate(table.rows[1:], start=2):
                if max(qty, unit, total) >= len(row):
                    continue
                quantity, unit_price, line_total = (_money(row[index].text) for index in (qty, unit, total))
                if quantity is None or unit_price is None or line_total is None:
                    continue
                checks += 1
                if abs(quantity * unit_price - line_total) > max(_TOLERANCE, abs(line_total) * Decimal("0.01")):
                    failures += 1
                    tasks.append(_conflict_task(table, row_number, row[total], f"r{row_number}c{total + 1}", f"{quantity} × {unit_price} ≠ {line_total}"))
            if checks:
                results.append(ValidationResult("line_item_arithmetic", "invalid" if failures else "valid", f"Checked {checks} line item relationship(s); {failures} conflict(s)."))
        subtotal = _header_index(headers, {"subtotal", "tamtinh"})
        tax = _header_index(headers, {"tax", "vat", "thue"})
        grand = _header_index(headers, {"grandtotal", "totaldue", "tongcong", "tongtien"})
        if subtotal is not None and tax is not None and grand is not None and len(table.rows) >= 2:
            row = table.rows[-1]
            if max(subtotal, tax, grand) < len(row):
                values = [_money(row[index].text) for index in (subtotal, tax, grand)]
                if all(value is not None for value in values):
                    expected = values[0] + values[1]
                    conflict = abs(expected - values[2]) > max(_TOLERANCE, abs(values[2]) * Decimal("0.01"))
                    results.append(ValidationResult("subtotal_tax_total", "invalid" if conflict else "valid", f"Subtotal + tax {'does not equal' if conflict else 'equals'} grand total."))
                    if conflict:
                        tasks.append(_conflict_task(table, len(table.rows), row[grand], f"r{len(table.rows)}c{grand + 1}", f"{values[0]} + {values[1]} ≠ {values[2]}"))
    if not results:
        results.append(ValidationResult("invoice_arithmetic", "uncertain", "No sufficiently labeled financial table relationship was found."))
    return results, tasks


def infer_field_status(value: Any, confidence: float | None, evidence: list[Any]) -> str:
    if value in (None, ""):
        return "not_found"
    if confidence is None or confidence < LOW_CONFIDENCE or not evidence:
        return "uncertain"
    return "valid"
