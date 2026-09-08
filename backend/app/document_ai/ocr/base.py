from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.document_ai.models import BoundingBox, Confidence


@dataclass
class OCRToken:
    text: str
    bbox: BoundingBox | None
    confidence: Confidence
    line_number: int = 0
    block_number: int = 0
    page_number: int = 1


@dataclass
class OCRPageResult:
    page_number: int
    width: int
    height: int
    text: str
    tokens: list[OCRToken] = field(default_factory=list)
    language: str | None = None
    engine: str = "unknown"
    warnings: list[str] = field(default_factory=list)
    selected_pass: int | None = None
    pass_scores: dict[str, float] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def average_confidence(self) -> float | None:
        if not self.tokens:
            return None
        return sum(token.confidence.value for token in self.tokens) / len(self.tokens)


class OCREngine(ABC):
    name = "abstract"

    @abstractmethod
    def recognize(self, image: Any, page_number: int, language: str = "eng") -> OCRPageResult:
        raise NotImplementedError

    def supports_language(self, language: str) -> bool:
        return language in {"eng"}
