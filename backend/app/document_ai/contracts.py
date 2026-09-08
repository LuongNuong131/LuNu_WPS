from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class DocumentState(str, Enum):
    UPLOADED = "uploaded"
    IDENTIFIED = "identified"
    PROFILED = "profiled"
    UNDERSTANDING = "understanding"
    STRUCTURED = "structured"
    EXTRACTED = "extracted"
    VALIDATED = "validated"
    REVIEW_REQUIRED = "review_required"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True)
class PipelineVersion:
    pipeline: str = "document-brain"
    pipeline_version: str = "4.0.0"
    ocr_version: str = "tesseract-adapter-1"
    layout_version: str = "heuristic-layout-1"
    table_version: str = "pdfplumber-table-2"
    semantic_version: str = "deterministic-semantic-2"
    export_version: str = "xlsx-audit-2"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class QualityDimensions:
    source_confidence: float | None = None
    ocr_confidence: float | None = None
    layout_confidence: float | None = None
    semantic_confidence: float | None = None
    consistency_confidence: float | None = None
    evidence_coverage: float | None = None
    overall: float | None = None
    explanations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewTask:
    task_id: str
    field: str
    value: Any
    status: str = "pending"
    priority: str = "normal"
    confidence: float = 0.0
    reason: str = "low_confidence"
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    rule: str
    status: str
    message: str
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
