from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.document_ai.models import DocumentProfile, DocumentQuality


@dataclass
class ProcessingPlan:
    stages: list[str] = field(default_factory=list)
    primary_engine: str = "native-pdf"
    fallback_engines: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    estimated_cost: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "stages": self.stages,
            "primary_engine": self.primary_engine,
            "fallback_engines": self.fallback_engines,
            "reason_codes": self.reason_codes,
            "estimated_cost": self.estimated_cost,
        }


class ProcessingRouter:
    def plan(self, profile: DocumentProfile, quality: DocumentQuality) -> ProcessingPlan:
        stages = ["ingest", "validate", "profile"]
        reasons: list[str] = []
        fallbacks: list[str] = []
        if profile.source_type == "native":
            stages.extend(["native_parse", "layout_analysis"])
            primary = "native-pdf"
            reasons.append("native_text_available")
        elif profile.source_type == "scan":
            stages.extend(["preprocess", "ocr", "layout_analysis"])
            primary = "tesseract"
            fallbacks.append("tesseract-single-language")
            reasons.append("image_only_document")
        else:
            stages.extend(["native_parse", "preprocess", "ocr", "layout_analysis"])
            primary = "hybrid"
            fallbacks.append("tesseract-single-language")
            reasons.append("mixed_native_and_image_pages")
        if profile.table_heavy:
            stages.extend(["table_detection", "table_structure", "table_validation"])
            reasons.append("table_heavy")
        if profile.complexity == "high":
            stages.append("reading_order")
            reasons.append("high_document_complexity")
        if quality.label == "low":
            stages.append("quality_review")
            reasons.append("low_scan_quality")
        return ProcessingPlan(
            stages=stages + ["canonicalize", "quality_validate", "export"],
            primary_engine=primary,
            fallback_engines=fallbacks,
            reason_codes=reasons,
            estimated_cost="high" if profile.complexity == "high" or profile.source_type == "scan" else "medium" if profile.table_heavy else "low",
        )
