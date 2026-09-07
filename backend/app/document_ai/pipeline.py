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
)
from app.document_ai.ocr.tesseract_engine import TesseractEngine
from app.document_ai.preprocess.image import prepare_for_ocr


class PDFIntelligencePipeline:
    """Create a canonical document model without coupling outputs to one converter."""

    def __init__(self, ocr_engine: TesseractEngine | None = None):
        self.ocr_engine = ocr_engine or TesseractEngine()

    def analyze(self, input_path: str, options: dict[str, Any] | None = None) -> CanonicalDocument:
        options = options or {}
        ocr_enabled = options.get("ocr_fallback", True) is not False
        ocr_language = options.get("ocr_language", "auto")
        document = CanonicalDocument(source_filename=Path(input_path).name, page_count=0)
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
    blocks: list[DocumentBlock] = []
    for index, word in enumerate(words, start=1):
        blocks.append(DocumentBlock(
            BlockType.TEXT,
            str(word.get("text", "")).strip(),
            BoundingBox(float(word.get("x0", 0)), float(word.get("top", 0)), float(word.get("x1", 0)), float(word.get("bottom", 0))),
            page_number,
            index,
            Confidence.from_score(0.98, "pdf-text"),
        ))
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
