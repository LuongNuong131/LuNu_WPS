from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _normal(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _cell_accuracy(expected: list[list[Any]], actual: list[list[Any]]) -> float:
    total = max(sum(len(row) for row in expected), 1)
    hits = sum(1 for r, row in enumerate(expected) for c, value in enumerate(row) if r < len(actual) and c < len(actual[r]) and _normal(value) == _normal(actual[r][c]))
    return hits / total


def _span_set(spans: list[dict[str, Any]]) -> set[tuple[int, int, int, int]]:
    return {(int(item["row"]), int(item["column"]), int(item.get("row_span", 1)), int(item.get("col_span", 1))) for item in spans}


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    expected = case.get("expected", {})
    actual = case.get("actual", {})
    cell_score = _cell_accuracy(expected.get("rows", []), actual.get("rows", []))
    expected_spans = _span_set(expected.get("merged_cells", []))
    actual_spans = _span_set(actual.get("merged_cells", []))
    span_score = len(expected_spans & actual_spans) / max(len(expected_spans), 1)
    expected_headers = expected.get("header_hierarchy", [])
    actual_headers = actual.get("header_hierarchy", [])
    header_score = sum(1 for item in expected_headers if item in actual_headers) / max(len(expected_headers), 1)
    structural = (cell_score + span_score + header_score) / 3
    return {"name": case.get("name", "unnamed"), "cell_accuracy": round(cell_score, 4), "merged_cell_recall": round(span_score, 4), "header_accuracy": round(header_score, 4), "structural_accuracy": round(structural, 4)}


def evaluate(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", payload if isinstance(payload, list) else [])
    results = [evaluate_case(case) for case in cases]
    average = sum(item["structural_accuracy"] for item in results) / max(len(results), 1)
    return {"dataset": str(path), "cases": results, "average_structural_accuracy": round(average, 4), "passed": average >= float(payload.get("pass_threshold", 0.9)) if isinstance(payload, dict) else average >= 0.9}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate LuNu WPS table extraction against golden JSON")
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.dataset), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
