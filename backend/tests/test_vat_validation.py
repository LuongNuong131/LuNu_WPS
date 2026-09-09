from app.document_ai.models import CanonicalDocument, Confidence, DocumentEntity, Evidence
from app.document_ai.validation import validate_document


def _entity(kind: str, raw: str, normalized):
    evidence = Evidence("invoice", 1, confidence=.95)
    return DocumentEntity(kind, raw, normalized, Confidence.from_score(.95, "test"), [evidence])


def test_vat_arithmetic_accepts_localized_invoice_values() -> None:
    document = CanonicalDocument("invoice.pdf", 1)
    document.entities = [
        _entity("Subtotal", "1.000.000 VNĐ", 1000000.0),
        _entity("VAT_Rate", "10%", .10),
        _entity("Grand_Total", "1.100.000 VNĐ", 1100000.0),
    ]
    results, tasks = validate_document(document)
    assert any(result.rule == "vat_arithmetic" and result.status == "valid" for result in results)
    assert not any(task.reason == "arithmetic_conflict" for task in tasks)


def test_vat_rate_is_inferred_from_subtotal_and_total() -> None:
    document = CanonicalDocument("invoice.pdf", 1)
    document.entities = [
        _entity("Subtotal", "1,000,000", 1000000.0),
        _entity("Grand_Total", "1,080,000", 1080000.0),
    ]
    results, _ = validate_document(document)
    assert document.diagnostics_data["inferred_vat_rate"] == .08
    assert any(result.rule == "vat_rate_inference" for result in results)
