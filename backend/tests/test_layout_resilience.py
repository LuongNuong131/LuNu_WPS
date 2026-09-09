from pathlib import Path

from PIL import Image, ImageDraw

from app.document_ai.layout.inference import cluster_columns
from app.document_ai.preprocess.image import prepare_for_ocr
from app.processors.pdf_to_excel import ExtractedTable, _merge_continuation_tables


def test_deskew_corrects_small_rotation() -> None:
    image = Image.new("RGB", (1200, 500), "white")
    draw = ImageDraw.Draw(image)
    draw.text((100, 180), "Invoice INV-2026-001 Total 1250000 VND", fill="black")
    rotated = image.rotate(4, expand=False, fillcolor="white")
    prepared = prepare_for_ocr(rotated, "deskew")
    assert prepared.deskew_angle != 0
    assert prepared.diagnostics["deskew_applied"] is True


def test_borderless_columns_are_density_clustered() -> None:
    clusters = cluster_columns([10, 12, 11, 100, 102, 180], tolerance=4)
    assert clusters == [[0, 1, 2], [3, 4], [5]]


def test_headerless_continuation_is_merged_when_structure_matches() -> None:
    tables = [
        ExtractedTable(1, 1, [["Item", "Amount"], ["A", "10"]], "lines", [1]),
        ExtractedTable(2, 1, [["B", "20"]], "text", [2]),
    ]
    merged, count = _merge_continuation_tables(tables)
    assert count == 1
    assert merged[0].rows == [["Item", "Amount"], ["A", "10"], ["B", "20"]]
