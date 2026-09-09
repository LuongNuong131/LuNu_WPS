from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber
import pymupdf
from PIL import Image

from app.document_ai.contracts import DocumentState
from app.document_ai.models import (
    BlockType,
    BoundingBox,
    CanonicalDocument,
    Confidence,
    DocumentBlock,
    DocumentCell,
    DocumentPage,
    DocumentTable,
    Evidence,
    ProcessingEvent,
)
from app.document_ai.ocr.tesseract_engine import TesseractEngine
from app.document_ai.preprocess.image import prepare_for_ocr
from app.document_ai.preprocess.noise_filter import filter_blocks, filter_text_lines
from app.document_ai.profile import DocumentProfiler
from app.document_ai.routing import ProcessingRouter
from app.document_ai.semantics import extract_entities
from app.document_ai.validation import validate_document
from app.document_ai.truth import build_truth_model


class PDFIntelligencePipeline:
    """Build a page-aware canonical document model for native and scanned PDFs."""

    def __init__(self, ocr_engine: TesseractEngine | None = None):
        self.ocr_engine = ocr_engine or TesseractEngine()

    def analyze(self, input_path: str, options: dict[str, Any] | None = None) -> CanonicalDocument:
        options = options or {}
        ocr_enabled = options.get("ocr_fallback", True) is not False
        ocr_language = options.get("ocr_language", "auto")
        document = CanonicalDocument(source_filename=Path(input_path).name, page_count=0)
        source, profile, quality, profile_diagnostics = DocumentProfiler().profile(input_path)
        document.source = source
        document.state = DocumentState.IDENTIFIED
        document.profile = profile
        document.state = DocumentState.PROFILED
        document.quality = quality
        document.quality_dimensions.source_confidence = round(1.0 if profile.source_type == "native" else 0.75 if profile.source_type == "mixed" else 0.55, 4)
        document.diagnostics_data.update(profile_diagnostics)
        plan = ProcessingRouter().plan(profile, quality)
        document.diagnostics_data["processing_plan"] = plan.to_dict()
        document.processing_history.append(ProcessingEvent(stage="profile", status="completed", details={"plan": plan.to_dict()}))
        document.state = DocumentState.UNDERSTANDING
        page_stats = {item["page"]: item for item in profile_diagnostics.get("page_stats", [])}
        ocr_diagnostics: list[dict[str, Any]] = []

        with pdfplumber.open(input_path) as pdf, pymupdf.open(input_path) as raster_pdf:
            document.page_count = len(pdf.pages)
            for page_number, page in enumerate(pdf.pages, start=1):
                canonical_page = DocumentPage(page_number, float(page.width), float(page.height), rotation=int(getattr(page, "rotation", 0) or 0))
                native_text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                canonical_page.raw_text = "\n".join(filter_text_lines(native_text.splitlines()))
                canonical_page.blocks = filter_blocks(_native_blocks(page, canonical_page.raw_text, page_number))
                canonical_page.tables = _native_tables(page, page_number)
                stats = page_stats.get(page_number, {})
                should_ocr = bool(ocr_enabled and stats.get("ocr_recommended", not canonical_page.blocks))
                if should_ocr:
                    ocr_result = self._ocr_page(raster_pdf[page_number - 1], page_number, ocr_language)
                    canonical_page.ocr_used = bool(ocr_result.tokens)
                    canonical_page.language = ocr_result.language
                    if ocr_result.tokens:
                        if native_text.strip():
                            canonical_page.raw_text = f"{native_text.strip()}\n{ocr_result.text.strip()}".strip()
                        else:
                            canonical_page.raw_text = ocr_result.text
                        canonical_page.blocks = filter_blocks(_ocr_blocks(ocr_result))
                    canonical_page.raw_text = "\n".join(filter_text_lines(canonical_page.raw_text.splitlines()))
                    if ocr_result.warnings:
                        document.warnings.extend(f"page_{page_number}:{warning}" for warning in ocr_result.warnings)
                    page_quality = dict(stats)
                    page_quality.update({
                        "ocr": True,
                        "engine": ocr_result.engine,
                        "language": ocr_result.language,
                        "selected_pass": ocr_result.selected_pass,
                        "pass_scores": ocr_result.pass_scores,
                        "average_confidence": ocr_result.average_confidence,
                        "diagnostics": ocr_result.diagnostics,
                    })
                    canonical_page.image_quality = page_quality
                    ocr_diagnostics.append({"page": page_number, **page_quality})
                else:
                    canonical_page.image_quality = {**stats, "ocr": False}
                document.pages.append(canonical_page)

        document.profile.languages = sorted({page.language for page in document.pages if page.language})
        document.profile.table_heavy = document.profile.table_heavy or bool(document.all_tables)
        ocr_confidences = [page.image_quality.get("average_confidence") for page in document.pages if page.ocr_used and page.image_quality.get("average_confidence") is not None]
        document.quality_dimensions.ocr_confidence = round(sum(ocr_confidences) / len(ocr_confidences), 4) if ocr_confidences else (1.0 if not any(page.ocr_used for page in document.pages) else 0.0)
        document.quality_dimensions.layout_confidence = round(sum(1.0 if page.reading_order else 0.0 for page in document.pages) / max(1, len(document.pages)), 4)
        document.diagnostics_data["ocr_pages"] = ocr_diagnostics
        document.processing_history.append(ProcessingEvent(stage="canonical_parse", status="completed"))
        if any(page.ocr_used for page in document.pages):
            document.processing_history.append(ProcessingEvent(stage="ocr", status="completed", engine=self.ocr_engine.name, details={"pages": [page.page_number for page in document.pages if page.ocr_used]}))
        _attach_provenance(document)
        document.entities = extract_entities(document)
        build_truth_model(document)
        document.state = DocumentState.EXTRACTED
        document.diagnostics_data["entities"] = len(document.entities)
        document.diagnostics_data["facts"] = len(document.facts)
        document.diagnostics_data["graph_edges"] = len(document.graph_edges)
        document.validation_results, document.review_tasks = validate_document(document)
        valid_results = sum(1 for result in document.validation_results if result.status == "valid")
        document.quality_dimensions.consistency_confidence = round(valid_results / max(1, len(document.validation_results)), 4)
        entity_confidences = [entity.confidence.value for entity in document.entities if entity.confidence]
        document.quality_dimensions.semantic_confidence = round(sum(entity_confidences) / len(entity_confidences), 4) if entity_confidences else None
        dimensions = [value for value in (document.quality_dimensions.source_confidence, document.quality_dimensions.ocr_confidence, document.quality_dimensions.layout_confidence, document.quality_dimensions.semantic_confidence, document.quality_dimensions.consistency_confidence, document.quality_dimensions.evidence_coverage) if value is not None]
        document.quality_dimensions.overall = round(sum(dimensions) / len(dimensions), 4) if dimensions else None
        if document.review_tasks:
            document.state = DocumentState.REVIEW_REQUIRED
            document.warnings.append(f"review_required:{len(document.review_tasks)}")
        else:
            document.state = DocumentState.READY
        document.processing_history.append(ProcessingEvent(stage="validation", status="completed", details={"review_tasks": len(document.review_tasks), "state": document.state.value}))
        return document

    def _ocr_page(self, pdf_page: Any, page_number: int, language: str):
        pixmap = pdf_page.get_pixmap(matrix=pymupdf.Matrix(2.2, 2.2), alpha=False)
        image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        prepared = prepare_for_ocr(image, "contrast")
        result = self.ocr_engine.recognize(prepared.image, page_number, language)
        result.warnings.extend(prepared.warnings)
        result.diagnostics["preprocessing_profile"] = prepared.profile
        result.diagnostics["deskew_angle"] = prepared.deskew_angle
        result.diagnostics["deskew_applied"] = bool(prepared.deskew_angle)
        result.diagnostics["raster_size"] = [pixmap.width, pixmap.height]
        prepared.image.close()
        image.close()
        return result


def _native_blocks(page: Any, text: str, page_number: int) -> list[DocumentBlock]:
    words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False) or []
    if not words and text:
        return [DocumentBlock(BlockType.TEXT, line.strip(), page_number=page_number, reading_order=index + 1, confidence=Confidence.from_score(0.98, "pdf-text")) for index, line in enumerate(text.splitlines()) if line.strip()]
    ordered = sorted(words, key=lambda word: (float(word.get("top", 0)), float(word.get("x0", 0))))
    lines: list[list[dict[str, Any]]] = []
    for word in ordered:
        if not lines or abs(float(word.get("top", 0)) - float(lines[-1][0].get("top", 0))) > 4:
            lines.append([word])
        else:
            lines[-1].append(word)
    blocks: list[DocumentBlock] = []
    for index, line in enumerate(lines, start=1):
        line = sorted(line, key=lambda word: float(word.get("x0", 0)))
        x0 = min(float(word.get("x0", 0)) for word in line)
        top = min(float(word.get("top", 0)) for word in line)
        x1 = max(float(word.get("x1", 0)) for word in line)
        bottom = max(float(word.get("bottom", 0)) for word in line)
        blocks.append(DocumentBlock(BlockType.TEXT, " ".join(str(word.get("text", "")).strip() for word in line), BoundingBox(x0, top, x1, bottom), page_number, index, Confidence.from_score(0.98, "pdf-text")))
    return blocks


def _native_tables(page: Any, page_number: int) -> list[DocumentTable]:
    tables: list[DocumentTable] = []
    strategies = [
        {"vertical_strategy": "lines", "horizontal_strategy": "lines", "intersection_tolerance": 5},
        {"vertical_strategy": "text", "horizontal_strategy": "text", "text_x_tolerance": 3, "text_y_tolerance": 3, "min_words_vertical": 2},
    ]
    signatures: set[tuple] = set()
    for settings in strategies:
        try:
            extracted = page.extract_tables(table_settings=settings) or []
        except Exception:
            continue
        for raw in extracted:
            normalized = [[_clean(value) for value in row] for row in raw or []]
            normalized = [row for row in normalized if any(row)]
            signature = (page_number, len(normalized), max((len(row) for row in normalized), default=0), tuple(tuple(row) for row in normalized[:3]), tuple(tuple(row) for row in normalized[-2:]))
            if len(normalized) < 2 or signature in signatures:
                continue
            signatures.add(signature)
            rows = [[DocumentCell(value, confidence=Confidence.from_score(0.9, "pdf-table"), data_type=_data_type(value), page_number=page_number) for value in row] for row in normalized]
            tables.append(DocumentTable(page_number, rows, source="pdfplumber", confidence=Confidence.from_score(0.9, "pdf-table")))
    return tables


def _attach_provenance(document: CanonicalDocument) -> None:
    document_id = document.source.fingerprint if document.source and document.source.fingerprint else document.source_filename
    for page in document.pages:
        page.reading_order = []
        for index, block in enumerate(page.blocks, start=1):
            block.block_id = block.block_id or f"p{page.page_number}-b{index}"
            page.reading_order.append(block.block_id)
            confidence = block.confidence.value if block.confidence else 0.0
            evidence = Evidence(document_id, page.page_number, block.bbox, block_id=block.block_id, quote=block.text[:500], engine=block.confidence.source if block.confidence else "unknown", confidence=confidence)
            block.evidence = [evidence]
            document.provenance.append(evidence)
        for table_index, table in enumerate(page.tables, start=1):
            table.table_id = table.table_id or f"p{page.page_number}-t{table_index}"
            table_confidence = table.confidence.value if table.confidence else 0.0
            table.evidence = [Evidence(document_id, page.page_number, table.bbox, table_id=table.table_id, engine=table.source, confidence=table_confidence)]
            document.provenance.extend(table.evidence)
            for row_index, row in enumerate(table.rows, start=1):
                for column_index, cell in enumerate(row, start=1):
                    cell.cell_id = cell.cell_id or f"{table.table_id}-r{row_index}-c{column_index}"
                    cell.page_number = page.page_number
                    confidence = cell.confidence.value if cell.confidence else table_confidence
                    cell.evidence = [Evidence(document_id, page.page_number, cell.bbox, table_id=table.table_id, cell_id=cell.cell_id, quote=cell.text[:500], engine=cell.confidence.source if cell.confidence else table.source, confidence=confidence)]
                    document.provenance.extend(cell.evidence)


def _ocr_blocks(result: Any) -> list[DocumentBlock]:
    grouped: dict[tuple[int, int], list[Any]] = {}
    for token in result.tokens:
        grouped.setdefault((token.block_number, token.line_number), []).append(token)
    blocks: list[DocumentBlock] = []
    for index, tokens in enumerate(sorted(grouped.values(), key=lambda group: (min(t.bbox.top for t in group if t.bbox), min(t.bbox.x0 for t in group if t.bbox))), start=1):
        tokens = sorted(tokens, key=lambda token: token.bbox.x0 if token.bbox else 0)
        boxes = [token.bbox for token in tokens if token.bbox]
        bbox = BoundingBox(min(box.x0 for box in boxes), min(box.top for box in boxes), max(box.x1 for box in boxes), max(box.bottom for box in boxes)) if boxes else None
        confidence = sum(token.confidence.value for token in tokens) / max(1, len(tokens))
        blocks.append(DocumentBlock(BlockType.TEXT, " ".join(token.text for token in tokens), bbox, tokens[0].page_number, index, Confidence.from_score(confidence, result.engine), attributes={"line": tokens[0].line_number, "block": tokens[0].block_number, "engine": result.engine, "selected_pass": result.selected_pass}))
    return blocks


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()


def _data_type(value: str) -> str:
    if not value:
        return "empty"
    compact = value.replace(" ", "")
    if re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?", compact):
        return "number"
    if re.fullmatch(r"\d{1,4}[/-]\d{1,2}[/-]\d{1,4}", value):
        return "date"
    if re.search(r"[$€£₫%]|\b(?:VND|USD|EUR)\b", value, re.I):
        return "currency"
    return "text"
