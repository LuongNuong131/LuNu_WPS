from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
from typing import Any

import pdfplumber
import pytesseract
from PIL import Image, ImageOps, ImageFilter
import pymupdf
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.document_ai.pipeline import PDFIntelligencePipeline
from app.document_ai.layout.inference import collapse_multiline_rows, column_width_vector, infer_header_hierarchy, infer_spans, vector_similarity, weighted_table_similarity
from app.processors.base import DocumentProcessor


@dataclass
class ExtractedTable:
    page: int
    index: int
    rows: list[list[str]]
    strategy: str
    source_pages: list[int] | None = None

    @property
    def header(self) -> tuple[str, ...]:
        return _header_signature(self.rows)

    @property
    def structure_key(self) -> str:
        """Stable human-readable key used to route structurally similar tables."""
        return f"{len(self.rows[0]) if self.rows else 0}:{'|'.join(self.header)}"


class PDFToExcelProcessor(DocumentProcessor):
    """Convert table-based and text-based PDFs into a structured workbook.

    The processor intentionally keeps a text fallback so a PDF with no detectable
    ruling lines still produces a complete, inspectable Excel output rather than
    failing with an empty workbook.
    """

    def __init__(self):
        self.last_diagnostics: dict[str, Any] = {}

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
        document = None
        page_count = 0
        ocr_used = False
        if options.get("use_canonical", True) is not False:
            document = PDFIntelligencePipeline().analyze(input_paths[0], options)
            self.last_diagnostics = document.diagnostics()
            self.last_diagnostics["extraction_mode"] = extraction_mode
            page_count = document.page_count
            ocr_used = any(page.ocr_used for page in document.pages)
            for page in document.pages:
                if include_text or document is not None:
                    for line_number, line in enumerate(page.raw_text.splitlines(), start=1):
                        clean_line = _clean_cell(line)
                        if clean_line:
                            text_rows.append([page.page_number, line_number, clean_line])
                if extraction_mode != "text":
                    for table_index, table in enumerate(page.tables, start=1):
                        rows = _normalize_rows([[cell.text for cell in row] for row in table.rows])
                        if len(rows) >= 2:
                            tables.append(ExtractedTable(page.page_number, table_index, rows, table.source, [page.page_number]))
        else:
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

        tables, merged_table_count = _merge_continuation_tables(tables)
        primary_tables, dynamic_groups = _route_tables(tables)

        workbook = Workbook(write_only=True)
        summary = workbook.create_sheet("Overview")
        _write_overview(summary, input_paths[0], page_count, tables, text_rows, ocr_used, document)
        line_items = workbook.create_sheet("Line Items")
        if primary_tables:
            table = primary_tables[0]
            _write_table(line_items, table.rows, table.page, table.strategy, table.source_pages, streaming=True)
        else:
            line_items.append(["No primary invoice table detected"])
        for group in dynamic_groups.values():
            table = group[0]
            sheet_name = _semantic_sheet_name(table, workbook)
            sheet = workbook.create_sheet(sheet_name)
            _write_table(sheet, table.rows, table.page, table.strategy, table.source_pages, streaming=True)
            for continuation in group[1:]:
                sheet.append([])
                sheet.append([f"Additional table from page {continuation.page}"])
                for row in continuation.rows:
                    sheet.append([_typed_excel_value(value) for value in row])
        if include_text or document is not None:
            text_sheet = workbook.create_sheet("Document_Text")
            _write_text_sheet(text_sheet, text_rows)
        audit_sheet = workbook.create_sheet("Audit")
        _write_audit_sheet(audit_sheet, document, tables)
        # Compatibility aliases are appended after the canonical five sheets so
        # older consumers keep working without changing the new contract/order.
        if "Document_Text" in workbook.sheetnames:
            legacy_text = workbook.create_sheet("Document Text")
            _write_text_sheet(legacy_text, text_rows)
        if dynamic_groups:
            legacy_table = workbook.create_sheet(_safe_sheet_name("Page 1 - Table 1", workbook))
            first_dynamic = next(iter(dynamic_groups.values()))[0]
            _write_table(legacy_table, first_dynamic.rows, first_dynamic.page, first_dynamic.strategy, first_dynamic.source_pages, streaming=True)
        if document is not None:
            self.last_diagnostics["document_state"] = document.state.value
            self.last_diagnostics["quality_dimensions"] = document.quality_dimensions.to_dict()
            self.last_diagnostics["validation_results"] = [item.to_dict() for item in document.validation_results]
            self.last_diagnostics["review_tasks"] = [item.to_dict() for item in document.review_tasks]
            self.last_diagnostics["facts_count"] = len(document.facts)
            self.last_diagnostics["graph_edges_count"] = len(document.graph_edges)
            self.last_diagnostics["truth_facts"] = [item.to_dict() for item in document.facts]
            self.last_diagnostics["truth_graph_edges"] = [item.to_dict() for item in document.graph_edges]
        self.last_diagnostics["audit_available"] = True
        self.last_diagnostics["workbook_sheets"] = list(workbook.sheetnames)
        self.last_diagnostics["table_quality"] = [_table_quality(table) for table in tables]
        self.last_diagnostics["primary_table_count"] = len(primary_tables)
        self.last_diagnostics["dynamic_table_groups"] = {key: [item.page for item in value] for key, value in dynamic_groups.items()}
        self.last_diagnostics["merged_table_count"] = merged_table_count
        self.last_diagnostics["multi_page_tables"] = sum(1 for table in tables if len(table.source_pages or [table.page]) > 1)
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
            found.append(ExtractedTable(page_number, len(found) + 1, rows, strategy_name, [page_number]))
    return found


def _merge_continuation_tables(tables: list[ExtractedTable]) -> tuple[list[ExtractedTable], int]:
    """Merge adjacent tables using structural and semantic evidence.

    A continuation may omit its header. In that case column count, normalized
    width vector and the data types of the first data row must still agree.
    """
    merged: list[ExtractedTable] = []
    merge_count = 0
    for table in tables:
        current = table
        current_pages = current.source_pages or [current.page]
        if merged:
            previous = merged[-1]
            previous_pages = previous.source_pages or [previous.page]
            can_merge = current_pages[0] == previous_pages[-1] + 1 and _continuation_match(previous, current)
            if can_merge:
                has_repeated_header = _header_signature(previous.rows) == _header_signature(current.rows[:1])
                previous.rows.extend(current.rows[1:] if has_repeated_header else current.rows)
                previous.source_pages = previous_pages + current_pages
                merge_count += 1
                continue
        current.source_pages = current_pages
        merged.append(current)
    return merged, merge_count


def _table_similarity(left: ExtractedTable, right: ExtractedTable) -> float:
    """Compare column count, fuzzy headers and tolerant width variance (0..1)."""
    left_width = len(left.rows[0]) if left.rows else 0
    right_width = len(right.rows[0]) if right.rows else 0
    if not left_width or left_width != right_width:
        return 0.0
    return weighted_table_similarity(
        left.header,
        right.header,
        column_width_vector(left.rows[1:] or left.rows),
        column_width_vector(right.rows[1:] or right.rows),
    )


def _route_tables(tables: list[ExtractedTable]) -> tuple[list[ExtractedTable], dict[str, list[ExtractedTable]]]:
    """Route the first invoice-like structure to Line Items and others by structure."""
    if not tables:
        return [], {}
    primary = tables[0]
    dynamic: dict[str, list[ExtractedTable]] = {}
    for table in tables[1:]:
        key = next((existing_key for existing_key, members in dynamic.items() if _table_similarity(members[0], table) >= 0.78), table.structure_key)
        dynamic.setdefault(key, []).append(table)
    return [primary], dynamic


def _header_signature(rows: list[list[str]]) -> tuple[str, ...]:
    if not rows:
        return ()
    return tuple(re.sub(r"\s+", " ", value).strip().casefold() for value in rows[0])


def _cell_type(value: str) -> str:
    value = _clean_cell(value)
    if not value:
        return "empty"
    if re.search(r"[$€£₫%]|\b(?:VND|USD|EUR)\b", value, re.I):
        return "number"
    if re.fullmatch(r"[-+]?\d[\d.,]*", value.replace(" ", "")):
        return "number"
    return "text"


def _continuation_match(previous: ExtractedTable, current: ExtractedTable) -> bool:
    previous_width = len(previous.rows[0]) if previous.rows else 0
    current_width = max((len(row) for row in current.rows), default=0)
    if previous_width < 2 or current_width != previous_width:
        return False
    if _header_signature(previous.rows) == _header_signature(current.rows[:1]):
        return True
    previous_vector = column_width_vector(previous.rows[1:] or previous.rows)
    current_data = current.rows[1:] if _header_signature(current.rows) == _header_signature(previous.rows) else current.rows
    current_vector = column_width_vector(current_data)
    similarity = weighted_table_similarity(
        previous.header,
        _header_signature(current.rows[:1]) or previous.header,
        previous_vector,
        current_vector,
    )
    if similarity < 0.78 and vector_similarity(previous_vector, current_vector) < 0.82:
        return False
    previous_types = [_cell_type(row[index]) for row in (previous.rows[1:2] or previous.rows) for index in range(previous_width)]
    current_types = [_cell_type(row[index]) for row in (current_data[:1] or current.rows) for index in range(current_width)]
    return sum(a == b or "empty" in {a, b} for a, b in zip(previous_types, current_types)) / previous_width >= 0.75


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
    return collapse_multiline_rows(normalized, description_column=0, numeric_columns=range(1, len(header)))


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


def _write_overview(sheet, input_path: str, page_count: int, tables: list[ExtractedTable], text_rows: list[list[Any]], ocr_used: bool, document: Any = None) -> None:
    rows = [
        ["OfficeFlow PDF → Excel", "Extraction report"],
        ["Source file", input_path.split("/")[-1]],
        ["Pages scanned", page_count],
        ["Tables detected", len(tables)],
        ["Text lines preserved", len(text_rows)],
        ["OCR fallback", "Used for image-only or low-quality pages" if ocr_used else "Not needed"],
        ["Extraction note", "Each detected table is kept in its own sheet. Document Text preserves text from every page."],
        ["Audit sheet", "Audit contains source cell text, confidence and provenance when canonical processing is enabled."],
    ]
    for row in rows:
        sheet.append(row)
    sheet.append([])
    sheet.append(["Invoice metadata", "Value", "Page", "Confidence", "Evidence"])
    if document is not None:
        preferred = {"Invoice_Number", "Date", "Tax_Code", "VAT_Rate", "Subtotal", "Grand_Total"}
        for entity in document.entities:
            if entity.entity_type in preferred:
                evidence = entity.evidence[0] if entity.evidence else None
                sheet.append([entity.entity_type, entity.normalized_value if entity.normalized_value is not None else entity.raw_value, evidence.page_number if evidence else "", entity.confidence.value if entity.confidence else None, json.dumps(evidence.to_dict(), ensure_ascii=False) if evidence else ""])
    sheet.append([])
    sheet.append(["Table", "Page", "Strategy", "Rows", "Columns"])
    for table in tables:
        sheet.append([f"Table {table.index}", ", ".join(map(str, table.source_pages or [table.page])), table.strategy, len(table.rows) - 1, len(table.rows[0])])
    if not getattr(sheet.parent, "write_only", False):
        for row in sheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        sheet.column_dimensions["A"].width = 24
        sheet.column_dimensions["B"].width = 42
        sheet.column_dimensions["C"].width = 16
        sheet.column_dimensions["D"].width = 64


def _write_table(sheet, rows: list[list[str]], page: int, strategy: str, source_pages: list[int] | None = None, streaming: bool = False) -> None:
    pages = ", ".join(map(str, source_pages or [page]))
    sheet.append([f"Source pages: {pages}", f"Detection: {strategy}"])
    sheet.append([])
    for row in rows:
        sheet.append([_typed_excel_value(value) for value in row])
    if not streaming:
        for row in sheet.iter_rows(min_row=3, max_row=sheet.max_row):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
    if rows and rows[0]:
        sheet.column_dimensions["A"].width = min(60, max(24, max(len(line) for line in rows[0][0].splitlines())))
    if streaming:
        sheet.freeze_panes = "A4"
        return
    for span in infer_spans(rows):
        start_row = span.row + 4
        start_col = span.column + 1
        sheet.merge_cells(start_row=start_row, start_column=start_col, end_row=span.end_row + 4, end_column=span.end_column + 1)
    hierarchy = infer_header_hierarchy(rows)
    if hierarchy.get("header_rows", 0) > 1:
        sheet.cell(row=2, column=1).value = "Header hierarchy"
        sheet.cell(row=2, column=2).value = json.dumps(hierarchy, ensure_ascii=False)
    sheet.freeze_panes = "A4"
    sheet.auto_filter.ref = f"A3:{get_column_letter(len(rows[0]))}{len(rows) + 2}"


def _typed_excel_value(value: str) -> Any:
    """Type only unambiguous numeric/currency values; preserve all other raw text."""
    raw = _clean_cell(value)
    if not raw:
        return ""
    compact = raw.replace(" ", "")
    has_currency = bool(re.search(r"[$€£₫]|\b(?:VND|USD|EUR)\b|VNĐ", raw, re.I))
    candidate = re.sub(r"[^0-9,.-]", "", compact)
    if not re.fullmatch(r"[-+]?\d[\d.,]*", candidate):
        return raw
    if candidate.count(",") and candidate.count("."):
        decimal_separator = "." if candidate.rfind(".") > candidate.rfind(",") else ","
        thousands_separator = "," if decimal_separator == "." else "."
        candidate = candidate.replace(thousands_separator, "").replace(decimal_separator, ".")
    elif has_currency and candidate.count(".") > 1 and not candidate.endswith("."):
        candidate = candidate.replace(".", "")
    elif candidate.count(",") > 1:
        candidate = candidate.replace(",", "")
    try:
        number = Decimal(candidate)
    except InvalidOperation:
        return raw
    if abs(number) > Decimal("1e15"):
        return raw
    return int(number) if number == number.to_integral_value() else float(number)


def _table_quality(table: ExtractedTable) -> dict[str, Any]:
    width = max((len(row) for row in table.rows), default=0)
    cells = [cell for row in table.rows for cell in row]
    non_empty = sum(bool(cell) for cell in cells)
    return {
        "page": table.page,
        "source_pages": table.source_pages or [table.page],
        "table": table.index,
        "strategy": table.strategy,
        "rows": max(0, len(table.rows) - 1),
        "columns": width,
        "cell_density": round(non_empty / max(1, len(cells)), 3),
        "empty_cell_ratio": round(1 - (non_empty / max(1, len(cells))), 3),
        "header_repeated": any(row == table.rows[0] for row in table.rows[1:]) if table.rows else False,
    }


def _write_audit_sheet(sheet, document: Any, tables: list[ExtractedTable]) -> None:
    sheet.append(["Kind", "Page", "Object ID", "Raw value / quote", "Confidence", "Engine", "Evidence"])
    if document is not None:
        sheet.append(["document", "", "state", document.state.value, document.quality_dimensions.overall, "pipeline", json.dumps({"quality": document.quality_dimensions.to_dict(), "review_tasks": len(document.review_tasks), "facts": len(document.facts), "graph_edges": len(document.graph_edges)}, ensure_ascii=False)])
        for fact in document.facts:
            sheet.append(["fact", fact.page_number, fact.fact_id, f"{fact.name}: {fact.raw_value}", fact.confidence, fact.status.value, json.dumps({"normalized_value": fact.normalized_value, "evidence": fact.evidence, "explanation": fact.explanation}, ensure_ascii=False)])
        for edge in document.graph_edges:
            sheet.append(["graph_edge", "", edge.subject, edge.predicate + " → " + edge.object, edge.confidence, "derived", json.dumps({"evidence": edge.evidence}, ensure_ascii=False)])
        for page in document.pages:
            for block in page.blocks:
                evidence = block.evidence[0] if block.evidence else None
                sheet.append(["block", page.page_number, block.block_id, block.text, block.confidence.value if block.confidence else None, block.confidence.source if block.confidence else "unknown", json.dumps(evidence.to_dict(), ensure_ascii=False) if evidence else ""])
            for table in page.tables:
                for row in table.rows:
                    for cell in row:
                        evidence = cell.evidence[0] if cell.evidence else None
                        sheet.append(["cell", page.page_number, cell.cell_id, cell.text, cell.confidence.value if cell.confidence else None, cell.confidence.source if cell.confidence else table.source, json.dumps(evidence.to_dict(), ensure_ascii=False) if evidence else ""])
    else:
        for table in tables:
            for row_index, row in enumerate(table.rows, start=1):
                for column_index, value in enumerate(row, start=1):
                    sheet.append(["legacy_cell", table.page, f"p{table.page}-t{table.index}-r{row_index}-c{column_index}", value, None, table.strategy, json.dumps({"page": table.page}, ensure_ascii=False)])
    sheet.freeze_panes = "A2"
    if not getattr(sheet.parent, "write_only", False):
        sheet.auto_filter.ref = f"A1:G{max(1, sheet.max_row)}"


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
    current_page = None
    for row in rows:
        page = row[0] if row else None
        if page != current_page:
            sheet.append([page, "", f"--- Page {page} ---"])
            current_page = page
        sheet.append(row)
    sheet.freeze_panes = "A2"
    if not getattr(sheet.parent, "write_only", False):
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


def _semantic_sheet_name(table: ExtractedTable, workbook: Workbook) -> str:
    """Infer a stable enterprise-friendly name from the table's headers."""
    header = " ".join(table.header)
    rules = (
        ("Packing_List", ("description", "item", "qty", "quantity", "weight", "mô tả", "số lượng", "trọng lượng")),
        ("Fee_Schedule", ("fee", "cost", "tax", "charge", "phí", "chi phí", "thuế")),
        ("Contacts", ("name", "email", "phone", "address", "tên", "điện thoại", "địa chỉ")),
        ("Inventory", ("sku", "stock", "warehouse", "inventory", "tồn kho", "mã hàng", "kho")),
        ("Payments", ("payment", "paid", "bank", "amount", "thanh toán", "ngân hàng", "số tiền")),
    )
    lowered = header.casefold()
    for name, keywords in rules:
        if sum(keyword.casefold() in lowered for keyword in keywords) >= 2:
            return _safe_sheet_name(f"{name}_Page{table.page}", workbook)
    return _safe_sheet_name(f"Table_Page{table.page}", workbook)


def _style_workbook(workbook: Workbook) -> None:
    if getattr(workbook, "write_only", False):
        return
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
