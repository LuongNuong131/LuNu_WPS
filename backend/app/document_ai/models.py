from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BlockType(str, Enum):
    TEXT = "text"
    HEADING = "heading"
    TABLE = "table"
    LIST = "list"
    IMAGE = "image"
    FORM = "form"
    UNKNOWN = "unknown"


@dataclass
class BoundingBox:
    x0: float
    top: float
    x1: float
    bottom: float

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)


@dataclass
class Confidence:
    value: float
    level: str = "medium"
    source: str = "unknown"

    @classmethod
    def from_score(cls, value: float, source: str) -> "Confidence":
        score = max(0.0, min(1.0, float(value)))
        level = "high" if score >= 0.90 else "medium" if score >= 0.70 else "low"
        return cls(score, level, source)


@dataclass
class DocumentCell:
    text: str
    bbox: BoundingBox | None = None
    row_span: int = 1
    col_span: int = 1
    confidence: Confidence | None = None
    data_type: str = "text"


@dataclass
class DocumentTable:
    page_number: int
    rows: list[list[DocumentCell]] = field(default_factory=list)
    bbox: BoundingBox | None = None
    source: str = "table-extractor"
    confidence: Confidence | None = None
    has_header: bool = True

    @property
    def column_count(self) -> int:
        return max((len(row) for row in self.rows), default=0)

    @property
    def row_count(self) -> int:
        return len(self.rows)


@dataclass
class DocumentBlock:
    block_type: BlockType
    text: str = ""
    bbox: BoundingBox | None = None
    page_number: int = 1
    reading_order: int = 0
    confidence: Confidence | None = None
    children: list["DocumentBlock"] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentPage:
    page_number: int
    width: float
    height: float
    rotation: int = 0
    blocks: list[DocumentBlock] = field(default_factory=list)
    tables: list[DocumentTable] = field(default_factory=list)
    raw_text: str = ""
    ocr_used: bool = False
    language: str | None = None


@dataclass
class CanonicalDocument:
    source_filename: str
    page_count: int
    pages: list[DocumentPage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    entities: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def all_tables(self) -> list[DocumentTable]:
        return [table for page in self.pages for table in page.tables]

    @property
    def all_blocks(self) -> list[DocumentBlock]:
        return [block for page in self.pages for block in page.blocks]

    def diagnostics(self) -> dict[str, Any]:
        confidences = [
            cell.confidence.value
            for table in self.all_tables
            for row in table.rows
            for cell in row
            if cell.confidence
        ]
        return {
            "pages": self.page_count,
            "tables": len(self.all_tables),
            "blocks": len(self.all_blocks),
            "ocr_pages": sum(1 for page in self.pages if page.ocr_used),
            "low_confidence_cells": sum(1 for value in confidences if value < 0.70),
            "average_cell_confidence": round(sum(confidences) / len(confidences), 3) if confidences else None,
            "warnings": self.warnings,
        }
