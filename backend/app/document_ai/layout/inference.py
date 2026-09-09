from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from math import sqrt
import re
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


@dataclass(frozen=True)
class TextFragment:
    text: str
    x0: float
    top: float
    x1: float
    bottom: float
    column: int = 0

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2

    @property
    def height(self) -> float:
        return max(1.0, self.bottom - self.top)


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
    for row in rows:
        for index, value in enumerate(row[:width]):
            counts[index] += len(str(value).strip())
    magnitude = sqrt(sum(value * value for value in counts)) or 1.0
    return [round(value / magnitude, 6) for value in counts]


def vector_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def normalized_header_score(left: Sequence[str], right: Sequence[str]) -> float:
    """Return average fuzzy header match, tolerant of OCR spacing and typos."""
    if not left or not right or len(left) != len(right):
        return 0.0
    scores = []
    for a, b in zip(left, right):
        clean_a = re.sub(r"[^a-z0-9]+", "", str(a).casefold())
        clean_b = re.sub(r"[^a-z0-9]+", "", str(b).casefold())
        scores.append(SequenceMatcher(None, clean_a, clean_b).ratio() if clean_a and clean_b else 1.0 if not clean_a and not clean_b else 0.0)
    return sum(scores) / len(scores)


def weighted_table_similarity(
    left_header: Sequence[str],
    right_header: Sequence[str],
    left_widths: Sequence[float],
    right_widths: Sequence[float],
    width_tolerance: float = 0.20,
) -> float:
    """Score table compatibility, relaxing width variance for matching headers.

    A header score above 85% permits up to 20% per-column width drift, which is
    common when scanned pages are slightly skewed or cropped.
    """
    if not left_header or len(left_header) != len(right_header):
        return 0.0
    header_score = normalized_header_score(left_header, right_header)
    if len(left_widths) != len(right_widths) or not left_widths:
        return header_score * 0.75
    variance = sum(abs(a - b) for a, b in zip(left_widths, right_widths)) / len(left_widths)
    tolerance = width_tolerance if header_score > 0.85 else width_tolerance / 2
    width_score = max(0.0, 1.0 - (variance / max(tolerance, 1e-9)))
    return round(0.7 * header_score + 0.3 * width_score, 4)


def cluster_fragments_by_y(fragments: Sequence[TextFragment], line_tolerance: float | None = None) -> list[list[TextFragment]]:
    """Cluster OCR/PDF fragments into visual lines using overlap and adaptive gaps."""
    if not fragments:
        return []
    ordered = sorted(fragments, key=lambda item: (item.top, item.x0))
    median_height = sorted(item.height for item in ordered)[len(ordered) // 2]
    tolerance = line_tolerance if line_tolerance is not None else max(2.0, median_height * 0.45)
    lines: list[list[TextFragment]] = []
    for fragment in ordered:
        candidates = [line for line in lines if _vertical_overlap(line, fragment) >= 0.35 or abs(_line_center(line) - fragment.center_y) <= tolerance]
        if not candidates:
            lines.append([fragment])
        else:
            target = min(candidates, key=lambda line: abs(_line_center(line) - fragment.center_y))
            target.append(fragment)
    return [sorted(line, key=lambda item: item.x0) for line in lines]


def _line_center(line: Sequence[TextFragment]) -> float:
    return sum(item.center_y for item in line) / max(1, len(line))


def _vertical_overlap(line: Sequence[TextFragment], fragment: TextFragment) -> float:
    top = max(min(item.top for item in line), fragment.top)
    bottom = min(max(item.bottom for item in line), fragment.bottom)
    overlap = max(0.0, bottom - top)
    return overlap / max(1.0, min(max(item.bottom for item in line) - min(item.top for item in line), fragment.height))


def collapse_multiline_rows(rows: Sequence[Sequence[str]], description_column: int = 0, numeric_columns: Sequence[int] | None = None) -> list[list[str]]:
    """Join visual continuation rows when only the description column has text.

    This is intentionally conservative: a non-empty numeric column starts a new
    logical item, while description-only rows are appended with a line break.
    """
    if not rows:
        return []
    width = max(len(row) for row in rows)
    normalized = [list(row) + [""] * (width - len(row)) for row in rows]
    numeric = set(numeric_columns or range(1, width))
    result: list[list[str]] = []
    for row in normalized:
        continuation = bool(row[description_column].strip()) and not any(row[index].strip() for index in numeric if index < width)
        if continuation and len(result) > 1 and not _looks_like_header(row, result[0]):
            result[-1][description_column] = f"{result[-1][description_column]}\n{row[description_column]}".strip()
        else:
            result.append(row)
    return result


def _looks_like_header(row: Sequence[str], header: Sequence[str]) -> bool:
    return [item.strip().casefold() for item in row] == [item.strip().casefold() for item in header]
