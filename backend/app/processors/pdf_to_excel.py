from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pdfplumber
import pytesseract
from PIL import Image, ImageOps, ImageFilter
import pymupdf
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.processors.base import DocumentProcessor


@dataclass
class ExtractedTable:
    page: int
    index: int
    rows: list[list[str]]
    strategy: str


class PDFToExcelProcessor(DocumentProcessor):
    """Convert table-based and text-based PDFs into a structured workbook.

    The processor intentionally keeps a text fallback so a PDF with no detectable
    ruling lines still produces a complete, inspectable Excel output rather than
    failing with an empty workbook.
    """

    def process(self, input_paths: list[str], output_path: str, options: dict | None = None) -> bool:
        if not input_paths:
            raise ValueError("Không có file PDF đầu vào.")
        options = options or {}
        extraction_mode = options.get("extraction", "auto")
        if extraction_mode not in {"auto", "tables", "text"}:
            raise ValueError("Extraction mode phải là auto, tables hoặc text.")
        include_text = options.get("include_text", True) is not False and extraction_mode != "tables"
        tables: list[ExtractedTable] = []
        text_rows: list[list[Any]] = []
        page_count = 0
        ocr_used = False
        with pdfplumber.open(input_paths[0]) as pdf:
            page_count = len(pdf.pages)
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                if include_text:
                    for line_number, line in enumerate(text.splitlines(), start=1):
                        clean_line = _clean_cell(line)
                        if clean_line:
                            text_rows.append([page_number, line_number, clean_line])
                if extraction_mode != "text":
                    tables.extend(_extract_page_tables(page, page_number))

        if not text_rows and options.get("ocr_fallback", True) is not False and extraction_mode != "tables":
            text_rows = _ocr_pdf(input_paths[0])
            ocr_used = bool(text_rows)

        if not tables and not text_rows:
            raise ValueError("PDF không chứa lớp văn bản hoặc bảng có thể trích xuất. Đây có thể là PDF scan; hãy bật OCR ở pipeline OCR.")

        workbook = Workbook()
        summary = workbook.active
        summary.title = "Overview"
        _write_overview(summary, input_paths[0], page_count, tables, text_rows, ocr_used)
        for table in tables:
            sheet_name = _safe_sheet_name(f"Page {table.page} · Table {table.index}", workbook)
            sheet = workbook.create_sheet(sheet_name)
            _write_table(sheet, table.rows, table.page, table.strategy)
        if include_text and text_rows:
            text_sheet = workbook.create_sheet("Document Text")
            _write_text_sheet(text_sheet, text_rows)
        _style_workbook(workbook)
        workbook.save(output_path)
        return True


def _extract_page_tables(page: pdfplumber.page.Page, page_number: int) -> list[ExtractedTable]:
    strategies = [
        ("lines", {"vertical_strategy": "lines", "horizontal_strategy": "lines", "intersection_tolerance": 5}),
        ("text", {"vertical_strategy": "text", "horizontal_strategy": "text", "text_x_tolerance": 3, "text_y_tolerance": 3, "min_words_vertical": 2, "min_words_horizontal": 1}),
    ]
    found: list[ExtractedTable] = []
    signatures: set[tuple] = set()
    for strategy_name, settings in strategies:
        try:
            raw_tables = page.extract_tables(table_settings=settings) or []
        except Exception:
            continue
        for raw in raw_tables:
            rows = _normalize_rows(raw)
            if len(rows) < 2 or max((len(row) for row in rows), default=0) < 2:
                continue
            signature = tuple(tuple(row) for row in rows[: min(4, len(rows))])
            if signature in signatures:
                continue
            signatures.add(signature)
            found.append(ExtractedTable(page_number, len(found) + 1, rows, strategy_name))
    return found


def _normalize_rows(raw_rows: list[list[Any]]) -> list[list[str]]:
    width = max((len(row or []) for row in raw_rows), default=0)
    rows: list[list[str]] = []
    for raw in raw_rows:
        values = [_clean_cell(value) for value in (raw or [])]
        values += [""] * (width - len(values))
        if any(values):
            rows.append(values)
    if len(rows) < 2:
        return rows
    header_index = _find_header_index(rows)
    header = _unique_headers(rows[header_index])
    data = rows[header_index + 1 :]
    normalized: list[list[str]] = [header]
    for row in data:
        if _is_repeated_header(row, header) or not any(row):
            continue
        normalized.append(row[: len(header)] + [""] * max(0, len(header) - len(row)))
    return normalized


def _find_header_index(rows: list[list[str]]) -> int:
    for index, row in enumerate(rows[:3]):
        filled = sum(bool(value) for value in row)
        if filled >= max(2, len(row) // 2):
            return index
    return 0


def _unique_headers(values: list[str]) -> list[str]:
    headers: list[str] = []
    counts: dict[str, int] = {}
    for index, value in enumerate(values, start=1):
        base = re.sub(r"\s+", " ", value).strip() or f"Column {index}"
        counts[base] = counts.get(base, 0) + 1
        headers.append(base if counts[base] == 1 else f"{base} ({counts[base]})")
    return headers


def _is_repeated_header(row: list[str], header: list[str]) -> bool:
    return [value.lower() for value in row] == [value.lower() for value in header]


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\u00a0", " ")).strip()


def _write_overview(sheet, input_path: str, page_count: int, tables: list[ExtractedTable], text_rows: list[list[Any]], ocr_used: bool) -> None:
    rows = [
        ["OfficeFlow PDF → Excel", "Extraction report"],
        ["Source file", input_path.split("/")[-1]],
        ["Pages scanned", page_count],
        ["Tables detected", len(tables)],
        ["Text lines preserved", len(text_rows)],
        ["OCR fallback", "Used for image-only pages" if ocr_used else "Not needed"],
        ["Extraction note", "Each detected table is kept in its own sheet. Document Text preserves text from every page."],
    ]
    for row in rows:
        sheet.append(row)
    sheet.append([])
    sheet.append(["Table", "Page", "Strategy", "Rows", "Columns"])
    for table in tables:
        sheet.append([f"Table {table.index}", table.page, table.strategy, len(table.rows) - 1, len(table.rows[0])])


def _write_table(sheet, rows: list[list[str]], page: int, strategy: str) -> None:
    sheet.append([f"Source page: {page}", f"Detection: {strategy}"])
    sheet.append([])
    for row in rows:
        sheet.append(row)
    sheet.freeze_panes = "A4"
    sheet.auto_filter.ref = f"A3:{get_column_letter(len(rows[0]))}{len(rows) + 2}"


def _ocr_pdf(input_path: str) -> list[list[Any]]:
    rows: list[list[Any]] = []
    with pymupdf.open(input_path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2.6, 2.6), alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            try:
                prepared = ImageOps.autocontrast(ImageOps.grayscale(image)).resize((image.width * 2, image.height * 2))
                prepared = prepared.filter(ImageFilter.SHARPEN)
                candidates = [pytesseract.image_to_string(prepared, config=f"--oem 3 --psm {psm}") or "" for psm in (6, 11)]
                text = max(candidates, key=_ocr_quality_score, default="")
                for line_number, line in enumerate(text.splitlines(), start=1):
                    clean_line = _clean_cell(line)
                    if clean_line:
                        rows.append([page_number, line_number, clean_line])
            finally:
                image.close()
    return rows


def _ocr_quality_score(text: str) -> tuple[int, int]:
    meaningful = sum(char.isalnum() for char in text)
    lines = sum(bool(line.strip()) for line in text.splitlines())
    return meaningful, lines


def _write_text_sheet(sheet, rows: list[list[Any]]) -> None:
    sheet.append(["Page", "Line", "Text"])
    for row in rows:
        sheet.append(row)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:C{len(rows) + 1}"


def _safe_sheet_name(name: str, workbook: Workbook) -> str:
    forbidden = r"[\\/*?:\[\]]"
    base = re.sub(forbidden, "-", name)[:28] or "Table"
    candidate = base
    counter = 2
    while candidate in workbook.sheetnames:
        candidate = f"{base[:25]}-{counter}"
        counter += 1
    return candidate


def _style_workbook(workbook: Workbook) -> None:
    navy = "10182F"
    cobalt = "4164EA"
    pale = "EEF2FF"
    muted = "66718A"
    thin = Side(style="thin", color="E3E7EF")
    for sheet in workbook.worksheets:
        sheet.sheet_view.showGridLines = False
        sheet.freeze_panes = sheet.freeze_panes or "A2"
        for cell in sheet[1]:
            cell.font = Font(name="Aptos Display", size=14, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor=navy)
            cell.alignment = Alignment(vertical="center")
        sheet.row_dimensions[1].height = 28
        for row in sheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                if cell.row > 1:
                    cell.border = Border(bottom=thin)
        if sheet.title == "Overview" and sheet.max_row >= 8:
            for cell in sheet[8]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor=cobalt)
        elif sheet.title != "Overview" and sheet.max_row >= 3:
            for cell in sheet[3]:
                cell.font = Font(bold=True, color=navy)
                cell.fill = PatternFill("solid", fgColor=pale)
        for column_cells in sheet.columns:
            letter = get_column_letter(column_cells[0].column)
            max_length = max((len(str(cell.value or "")) for cell in column_cells[:80]), default=10)
            sheet.column_dimensions[letter].width = min(max(max_length + 2, 12), 52)
        if sheet.title == "Document Text":
            sheet.column_dimensions["C"].width = 90
        for cell in sheet[1]:
            cell.font = Font(name="Aptos Display", size=14, bold=True, color="FFFFFF")
