from app.document_ai.models import CanonicalDocument, Confidence, DocumentCell, DocumentTable
from app.document_ai.validation import validate_document


def test_line_item_arithmetic_conflict_creates_high_priority_review() -> None:
    table = DocumentTable(page_number=1, table_id="p1-t1", rows=[
        [DocumentCell("Qty"), DocumentCell("Unit Price"), DocumentCell("Line Total")],
        [DocumentCell("2"), DocumentCell("100"), DocumentCell("250", confidence=Confidence.from_score(.95, "test"))],
    ])
    document = CanonicalDocument("invoice.pdf", 1, pages=[], facts=[])
    document.pages = []
    # all_tables is page-derived, so attach a minimal page-like object through the real model.
    from app.document_ai.models import DocumentPage
    document.pages = [DocumentPage(1, 100, 100, tables=[table])]
    results, tasks = validate_document(document)
    assert any(result.rule == "line_item_arithmetic" and result.status == "invalid" for result in results)
    assert any(task.reason == "arithmetic_conflict" and task.priority == "high" for task in tasks)
