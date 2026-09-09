from pathlib import Path

from app.document_ai.layout.inference import infer_header_hierarchy, infer_spans
from tests.benchmark.evaluate import evaluate


def test_infer_merged_cells_and_header_hierarchy() -> None:
    rows = [["Revenue", "", "Cost"], ["Q1", "Q2", "Total"], ["100", "120", "220"]]
    spans = infer_spans(rows)
    assert [(span.row, span.column, span.col_span) for span in spans] == [(0, 0, 2)]
    hierarchy = infer_header_hierarchy(rows)
    assert hierarchy["columns"][1]["parent"] == "Revenue"
    assert hierarchy["columns"][1]["child"] == "Q2"


def test_golden_dataset_reaches_threshold() -> None:
    result = evaluate(Path(__file__).parent / "benchmark" / "sample.json")
    assert result["passed"] is True
    assert result["average_structural_accuracy"] == 1.0
