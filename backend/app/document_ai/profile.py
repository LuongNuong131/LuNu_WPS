from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Any

import pdfplumber

from app.document_ai.models import DocumentProfile, DocumentQuality, DocumentSource


class DocumentProfiler:
    """Profile a PDF once and expose page-level processing signals."""

    def profile(self, input_path: str) -> tuple[DocumentSource, DocumentProfile, DocumentQuality, dict[str, Any]]:
        path = Path(input_path)
        source = DocumentSource(
            filename=path.name,
            mime_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            fingerprint=_fingerprint(path),
            byte_size=path.stat().st_size if path.exists() else None,
            source_type="pdf",
        )
        native_text_pages = 0
        blank_pages = 0
        image_heavy_pages = 0
        table_pages = 0
        low_quality_pages = 0
        page_stats: list[dict[str, Any]] = []
        warnings: list[str] = []

        with pdfplumber.open(input_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text(x_tolerance=2, y_tolerance=3) or "").strip()
                images = len(page.images or [])
                tables = len(page.find_tables() or [])
                chars = len(text)
                native_text = chars >= 24
                image_heavy = images > 0 and chars < 80
                blank = not text and images == 0
                vector_count = len(getattr(page, "rects", []) or []) + len(getattr(page, "lines", []) or [])
                table_signal = tables > 0 or vector_count >= 8
                quality_warnings: list[str] = []
                if blank:
                    quality_warnings.append("blank_page")
                if image_heavy:
                    quality_warnings.append("image_heavy")
                if 0 < chars < 24:
                    quality_warnings.append("sparse_native_text")
                if native_text:
                    native_text_pages += 1
                if blank:
                    blank_pages += 1
                if image_heavy:
                    image_heavy_pages += 1
                if table_signal:
                    table_pages += 1
                if image_heavy or (0 < chars < 24):
                    low_quality_pages += 1
                page_stats.append(
                    {
                        "page": page_number,
                        "width": round(float(page.width), 2),
                        "height": round(float(page.height), 2),
                        "rotation": int(getattr(page, "rotation", 0) or 0),
                        "text_chars": chars,
                        "images": images,
                        "tables": tables,
                        "vector_objects": vector_count,
                        "native_text": native_text,
                        "image_heavy": image_heavy,
                        "blank": blank,
                        "table_signal": table_signal,
                        "quality_warnings": quality_warnings,
                        "ocr_recommended": bool(not native_text or image_heavy or quality_warnings),
                    }
                )

        page_count = len(page_stats)
        ocr_pages = sum(1 for item in page_stats if item["ocr_recommended"])
        table_heavy = table_pages >= max(1, page_count // 3) if page_count else False
        source_type = "native" if native_text_pages == page_count and page_count else "scan" if native_text_pages == 0 else "mixed"
        complexity_score = min(
            100,
            (page_count * 2)
            + (table_pages * 5)
            + (image_heavy_pages * 6)
            + (low_quality_pages * 4)
            + (20 if table_heavy else 0),
        )
        complexity = "extreme" if complexity_score > 80 else "very_complex" if complexity_score > 60 else "complex" if complexity_score > 40 else "normal" if complexity_score > 20 else "easy"
        quality_label = "low" if blank_pages or image_heavy_pages else "medium" if ocr_pages else "high"
        if not page_count:
            warnings.append("empty_document")
        if image_heavy_pages:
            warnings.append("ocr_required_on_image_pages")
        if low_quality_pages:
            warnings.append("low_native_text_quality_on_some_pages")

        profile = DocumentProfile(
            document_type="pdf",
            source_type=source_type,
            complexity=complexity,
            languages=[],
            table_heavy=table_heavy,
            form_heavy=False,
            likely_handwriting=False,
            page_count=page_count,
        )
        quality = DocumentQuality(
            label=quality_label,
            score=round(1 - (ocr_pages / page_count), 3) if page_count else 0,
            native_text_pages=native_text_pages,
            ocr_pages=ocr_pages,
            blank_pages=blank_pages,
            low_resolution_pages=0,
            warnings=warnings,
        )
        diagnostics = {
            "page_stats": page_stats,
            "fingerprint": source.fingerprint,
            "complexity_score": complexity_score,
            "ocr_recommended_pages": [item["page"] for item in page_stats if item["ocr_recommended"]],
        }
        return source, profile, quality, diagnostics


def _fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
