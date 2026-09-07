from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber
import pymupdf
from PIL import Image

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
from app.document_ai.profile import DocumentProfiler
from app.document_ai.routing import ProcessingRouter
from app.document_ai.semantics import extract_entities


class PDFIntelligencePipeline:
    """Create a canonical document model without coupling outputs to one converter."""

    def __init__(self, ocr_engine: TesseractEngine | None = None):
        self.ocr_engine = ocr_engine or TesseractEngine()

    def analyze(self, input_path: str, options: dict[str, Any] | None = None) -> CanonicalDocument:
        options = options or {}
        ocr_enabled = options.get("ocr_fallback", True) is not False
        ocr_language = options.get("ocr_language", "auto")
        document = CanonicalDocument(source_filename=Path(input_path).name, page_count=0)
        source, profile, quality, profile_diagnostics = DocumentProfiler().profile(input_path)
        document.source = source
        document.profile = profile
        document.quality = quality
        document.diagnostics_data.update(profile_diagnostics)
        plan = ProcessingRouter().plan(profile, quality)
        document.diagnostics_data["processing_plan"] = plan.to_dict()
        document.processing_history.append(ProcessingEvent(stage="profile", status="completed", details={"plan": plan.to_dict()}))
        with pdfplumber.open(input_path) as pdf:
            document.page_count = len(pdf.pages)
            for page_number, page in enumerate(pdf.pages, start=1):
                canonical_page = DocumentPage(page_number, float(page.width), float(page.height), rotation=0)
                text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                canonical_page.raw_text = text
                canonical_page.blocks = _native_blocks(page, text, page_number)
                canonical_page.tables = _native_tables(page, page_number)
                if not canonical_page.blocks and ocr_enabled:
                    ocr_result = self._ocr_page(input_path, page_number, ocr_language)
                    canonical_page.ocr_used = bool(ocr_result.tokens)
                    canonical_page.language = ocr_result.language
                    canonical_page.raw_text = ocr_result.text
                    canonical_page.blocks = _ocr_blocks(ocr_result)
                    if ocr_result.warnings:
                        document.warnings.extend(ocr_result.warnings)
                document.pages.append(canonical_page)
        document.profile.languages = sorted({page.language for page in document.pages if page.language})
        document.profile.table_heavy = document.profile.table_heavy or bool(document.all_tables)
        document.processing_history.append(ProcessingEvent(stage="canonical_parse", status="completed"))
        if any(page.ocr_used for page in document.pages):
            document.processing_history.append(ProcessingEvent(stage="ocr", status="completed", engine=self.ocr_engine.name))
        _attach_provenance(document)
        document.entities = extract_entities(document)
        document.diagnostics_data["entities"] = len(document.entities)
        return document

    def _ocr_page(self, input_path: str, page_number: int, language: str):
        with pymupdf.open(input_path) as pdf:
            page = pdf[page_number - 1]
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2.2, 2.2), alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            prepared = prepare_for_ocr(image, "adaptive")
            result = self.ocr_engine.recognize(prepared.image, page_number, language)
            result.warnings.extend(prepared.warnings)
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
            signature = tuple(tuple(row) for row in normalized[:4])
            if len(normalized) < 2 or signature in signatures:
                continue
            signatures.add(signature)
            rows = []
            for row in normalized:
                rows.append([DocumentCell(value, confidence=Confidence.from_score(0.9, "pdf-table"), data_type=_data_type(value)) for value in row])
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
            evidence = Evidence(document_id, page.page_number, block.bbox, block_id=block.block_id, quote=block.text, engine=block.confidence.source if block.confidence else "unknown", confidence=confidence)
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
                    confidence = cell.confidence.value if cell.confidence else table_confidence
                    cell.evidence = [Evidence(document_id, page.page_number, cell.bbox, table_id=table.table_id, cell_id=cell.cell_id, quote=cell.text, engine=cell.confidence.source if cell.confidence else table.source, confidence=confidence)]
                    document.provenance.extend(cell.evidence)


def _ocr_blocks(result: Any) -> list[DocumentBlock]:
    blocks: list[DocumentBlock] = []
    for index, token in enumerate(result.tokens, start=1):
        blocks.append(DocumentBlock(BlockType.TEXT, token.text, token.bbox, token.page_number, index, token.confidence, attributes={"line": token.line_number, "block": token.block_number, "engine": result.engine}))
    return blocks


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()


def _data_type(value: str) -> str:
    if not value:
        return "empty"
    if re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?", value.replace(" ", "")):
        return "number"
    if re.fullmatch(r"\d{1,4}[/-]\d{1,2}[/-]\d{1,4}", value):
        return "date"
    if re.search(r"[$€£₫%]", value):
        return "currency"
    return "text"
