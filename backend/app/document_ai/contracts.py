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


class TruthStatus(str, Enum):
    OBSERVED = "observed"
    EXTRACTED = "extracted"
    NORMALIZED = "normalized"
    INFERRED = "inferred"
    VERIFIED = "verified"
    AI_GENERATED = "ai_generated"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"
    NOT_FOUND = "not_found"
    UNSUPPORTED = "unsupported"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class PipelineVersion:
    pipeline: str = "document-brain"
    pipeline_version: str = "5.0.0"
    ocr_version: str = "tesseract-adapter-1"
    layout_version: str = "heuristic-layout-1"
    table_version: str = "pdfplumber-table-2"
    semantic_version: str = "deterministic-semantic-3"
    export_version: str = "xlsx-audit-3"

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
class DocumentFact:
    fact_id: str
    name: str
    raw_value: Any
    normalized_value: Any = None
    status: TruthStatus = TruthStatus.EXTRACTED
    confidence: float = 0.0
    evidence: list[dict[str, Any]] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        return result


@dataclass
class GraphEdge:
    subject: str
    predicate: str
    object: str
    confidence: float = 0.0
    evidence: list[dict[str, Any]] = field(default_factory=list)

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
