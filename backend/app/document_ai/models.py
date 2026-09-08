from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.document_ai.contracts import DocumentFact, DocumentState, GraphEdge, PipelineVersion, QualityDimensions, ReviewTask, ValidationResult


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

    def as_list(self) -> list[float]:
        return [round(self.x0, 2), round(self.top, 2), round(self.x1, 2), round(self.bottom, 2)]


@dataclass
class Evidence:
    document_id: str
    page_number: int | None = None
    bbox: BoundingBox | None = None
    block_id: str | None = None
    table_id: str | None = None
    cell_id: str | None = None
    token_ids: list[str] = field(default_factory=list)
    quote: str | None = None
    engine: str = "unknown"
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "page": self.page_number,
            "bbox": self.bbox.as_list() if self.bbox else None,
            "block_id": self.block_id,
            "table_id": self.table_id,
            "cell_id": self.cell_id,
            "token_ids": self.token_ids,
            "quote": self.quote,
            "engine": self.engine,
            "confidence": round(self.confidence, 4),
        }


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
class DocumentSource:
    filename: str
    mime_type: str = "application/pdf"
    fingerprint: str | None = None
    byte_size: int | None = None
    source_type: str = "unknown"


@dataclass
class DocumentQuality:
    label: str = "unknown"
    score: float | None = None
    native_text_pages: int = 0
    ocr_pages: int = 0
    blank_pages: int = 0
    low_resolution_pages: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class DocumentProfile:
    document_type: str = "pdf"
    source_type: str = "unknown"
    complexity: str = "unknown"
    languages: list[str] = field(default_factory=list)
    table_heavy: bool = False
    form_heavy: bool = False
    likely_handwriting: bool = False
    page_count: int = 0


@dataclass
class ProcessingEvent:
    stage: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    engine: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentEntity:
    entity_type: str
    raw_value: str
    normalized_value: Any = None
    confidence: Confidence | None = None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class DocumentRelation:
    relation_type: str
    subject: str
    object: str
    confidence: Confidence | None = None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class DocumentCell:
    text: str
    bbox: BoundingBox | None = None
    row_span: int = 1
    col_span: int = 1
    confidence: Confidence | None = None
    data_type: str = "text"
    cell_id: str | None = None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class DocumentTable:
    page_number: int
    rows: list[list[DocumentCell]] = field(default_factory=list)
    bbox: BoundingBox | None = None
    source: str = "table-extractor"
    confidence: Confidence | None = None
    has_header: bool = True
    table_id: str | None = None
    evidence: list[Evidence] = field(default_factory=list)

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
    block_id: str | None = None
    evidence: list[Evidence] = field(default_factory=list)
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
    image_quality: dict[str, Any] = field(default_factory=dict)
    orientation: str = "upright"
    reading_order: list[str] = field(default_factory=list)
    headers: list[DocumentBlock] = field(default_factory=list)
    footers: list[DocumentBlock] = field(default_factory=list)


@dataclass
class CanonicalDocument:
    source_filename: str
    page_count: int
    pages: list[DocumentPage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source: DocumentSource | None = None
    profile: DocumentProfile | None = None
    quality: DocumentQuality | None = None
    entities: list[DocumentEntity] = field(default_factory=list)
    relations: list[DocumentRelation] = field(default_factory=list)
    facts: list[DocumentFact] = field(default_factory=list)
    graph_edges: list[GraphEdge] = field(default_factory=list)
    key_value_pairs: list[dict[str, Any]] = field(default_factory=list)
    diagnostics_data: dict[str, Any] = field(default_factory=dict)
    provenance: list[Evidence] = field(default_factory=list)
    processing_history: list[ProcessingEvent] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    state: DocumentState = DocumentState.UPLOADED
    pipeline_version: PipelineVersion = field(default_factory=PipelineVersion)
    quality_dimensions: QualityDimensions = field(default_factory=QualityDimensions)
    validation_results: list[ValidationResult] = field(default_factory=list)
    review_tasks: list[ReviewTask] = field(default_factory=list)
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
        result = {
            "pages": self.page_count,
            "tables": len(self.all_tables),
            "blocks": len(self.all_blocks),
            "ocr_pages": sum(1 for page in self.pages if page.ocr_used),
            "low_confidence_cells": sum(1 for value in confidences if value < 0.70),
            "average_cell_confidence": round(sum(confidences) / len(confidences), 3) if confidences else None,
            "profile": self.profile.__dict__ if self.profile else None,
            "quality": self.quality.__dict__ if self.quality else None,
            "processing_stages": [event.stage for event in self.processing_history],
            "warnings": [*self.warnings, *(self.quality.warnings if self.quality else [])],
            "state": self.state.value,
            "pipeline_version": self.pipeline_version.to_dict(),
            "quality_dimensions": self.quality_dimensions.to_dict(),
            "validation_results": [item.to_dict() for item in self.validation_results],
            "review_tasks": [item.to_dict() for item in self.review_tasks],
            "facts": [item.to_dict() for item in self.facts],
            "graph_edges": [item.to_dict() for item in self.graph_edges],
        }
        result.update(self.diagnostics_data)
        return result
