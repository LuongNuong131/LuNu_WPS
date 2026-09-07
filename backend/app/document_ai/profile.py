from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Any

import pdfplumber

from app.document_ai.models import DocumentProfile, DocumentQuality, DocumentSource


class DocumentProfiler:
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
        page_count = 0
        page_stats: list[dict[str, Any]] = []
        warnings: list[str] = []
        with pdfplumber.open(input_path) as pdf:
            page_count = len(pdf.pages)
            for page_number, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text(x_tolerance=2, y_tolerance=3) or "").strip()
                images = len(page.images or [])
                tables = len(page.find_tables() or [])
                if text:
                    native_text_pages += 1
                else:
                    blank_pages += 1 if images == 0 else 0
                if images and not text:
                    image_heavy_pages += 1
                if tables:
                    table_pages += 1
                page_stats.append({"page": page_number, "width": page.width, "height": page.height, "text_chars": len(text), "images": images, "tables": tables, "native_text": bool(text)})
        ocr_pages = max(0, page_count - native_text_pages)
        table_heavy = table_pages >= max(1, page_count // 3)
        source_type = "native" if native_text_pages == page_count else "scan" if native_text_pages == 0 else "mixed"
        complexity = "high" if table_heavy or page_count > 20 or image_heavy_pages > 5 else "medium" if page_count > 5 or ocr_pages else "low"
        quality_label = "low" if blank_pages or image_heavy_pages else "medium" if ocr_pages else "high"
        if page_count == 0:
            warnings.append("empty_document")
        if image_heavy_pages:
            warnings.append("ocr_required_on_image_pages")
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
            score=round((native_text_pages / page_count) if page_count else 0, 3),
            native_text_pages=native_text_pages,
            ocr_pages=ocr_pages,
            blank_pages=blank_pages,
            low_resolution_pages=0,
            warnings=warnings,
        )
        return source, profile, quality, {"page_stats": page_stats, "fingerprint": source.fingerprint}


def _fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
