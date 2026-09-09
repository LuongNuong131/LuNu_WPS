from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
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
            while r + row_span < len(matrix) and all(not matrix[r + row_span][x] and (r + row_span, x) not in covered for x in range(c, c + col_span)):
                row_span += 1
            if row_span > 1 or col_span > 1:
                span = CellSpan(r, c, row_span, col_span)
                spans.append(span)
                covered.update((rr, cc) for rr in range(span.row, span.end_row + 1) for cc in range(span.column, span.end_column + 1))
    return spans


def infer_header_hierarchy(rows: Sequence[Sequence[str]]) -> dict[str, object]:
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


def cluster_columns(x_centers: Sequence[float], tolerance: float = 12.0, min_samples: int = 1) -> list[list[int]]:
    """Density-based 1D clustering tolerant of small OCR alignment errors.

    A center joins a cluster when it is density-connected to a core neighborhood.
    Outliers remain singleton columns rather than being silently discarded.
    """
    if not x_centers:
        return []
    order = sorted(range(len(x_centers)), key=lambda i: x_centers[i])
    clusters: list[list[int]] = []
    current: list[int] = []
    for index in order:
        if not current:
            current = [index]
            continue
        neighborhood = [item for item in current if abs(x_centers[index] - x_centers[item]) <= tolerance]
        if len(neighborhood) >= min_samples or abs(x_centers[index] - sum(x_centers[item] for item in current) / len(current)) <= tolerance:
            current.append(index)
        else:
            clusters.append(current)
            current = [index]
    if current:
        clusters.append(current)
    return [sorted(cluster) for cluster in clusters]


def column_width_vector(rows: Sequence[Sequence[str]]) -> list[float]:
    width = max((len(row) for row in rows), default=0)
    if not width:
        return []
    counts = [0.0] * width
    total = max(1, len(rows))
    for row in rows:
        for index, value in enumerate(row[:width]):
            counts[index] += len(str(value).strip())
    magnitude = sqrt(sum(value * value for value in counts)) or 1.0
    return [round(value / magnitude, 6) for value in counts]


def vector_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))
