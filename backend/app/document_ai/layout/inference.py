from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class CellSpan:
    row: int
    column: int
    row_span: int = 1
    col_span: int = 1

    @property
    def end_row(self) -> int:
        return self.row + self.row_span - 1

    @property
    def end_column(self) -> int:
        return self.column + self.col_span - 1


def infer_spans(rows: Sequence[Sequence[str]]) -> list[CellSpan]:
    """Infer conservative rectangular spans from blank continuation cells.

    PDF table extractors commonly place a merged value in the top-left cell and
    emit empty cells for the covered area. We only merge when every covered cell
    is empty, preventing destructive guesses on ordinary sparse tables.
    """
    if not rows:
        return []
    width = max((len(row) for row in rows), default=0)
    matrix = [list(row) + [""] * (width - len(row)) for row in rows]
    spans: list[CellSpan] = []
    covered: set[tuple[int, int]] = set()
    for r, row in enumerate(matrix):
        for c, value in enumerate(row):
            if not value or (r, c) in covered:
                continue
            col_span = 1
            while c + col_span < width and not matrix[r][c + col_span] and (r, c + col_span) not in covered:
                col_span += 1
            row_span = 1
            while r + row_span < len(matrix) and all(
                not matrix[r + row_span][x] and (r + row_span, x) not in covered
                for x in range(c, c + col_span)
            ):
                row_span += 1
            if row_span > 1 or col_span > 1:
                span = CellSpan(r, c, row_span, col_span)
                spans.append(span)
                for rr in range(span.row, span.end_row + 1):
                    for cc in range(span.column, span.end_column + 1):
                        covered.add((rr, cc))
    return spans


def infer_header_hierarchy(rows: Sequence[Sequence[str]]) -> dict[str, object]:
    """Return parent/child header relationships without flattening source rows."""
    if len(rows) < 2:
        return {"header_rows": 1 if rows else 0, "columns": []}
    width = max((len(row) for row in rows), default=0)
    parents = list(rows[0]) + [""] * (width - len(rows[0]))
    children = list(rows[1]) + [""] * (width - len(rows[1]))
    columns = []
    active_parent = ""
    for index in range(width):
        parent = parents[index].strip() or active_parent
        child = children[index].strip()
        if parent:
            active_parent = parent
        columns.append({"column": index + 1, "parent": parent or None, "child": child or None, "path": [item for item in (parent, child) if item]})
    return {"header_rows": 2, "columns": columns}


def cluster_columns(x_centers: Sequence[float], tolerance: float = 12.0) -> list[list[int]]:
    """Cluster x-centers for borderless table detection using a deterministic rule."""
    clusters: list[list[int]] = []
    for index, center in sorted(enumerate(x_centers), key=lambda item: item[1]):
        if not clusters or abs(center - sum(x_centers[i] for i in clusters[-1]) / len(clusters[-1])) > tolerance:
            clusters.append([index])
        else:
            clusters[-1].append(index)
    return clusters
