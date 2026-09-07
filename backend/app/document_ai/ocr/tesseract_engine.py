from __future__ import annotations

from typing import Any

import pytesseract
from pytesseract import Output

from app.document_ai.models import BoundingBox, Confidence
from app.document_ai.ocr.base import OCREngine, OCRPageResult, OCRToken


class TesseractEngine(OCREngine):
    name = "tesseract"

    def __init__(self, default_language: str = "eng+vie", psm: int = 6):
        self.default_language = default_language
        self.psm = psm
        self.available_languages = set(pytesseract.get_languages(config=""))

    def resolve_language(self, requested: str | None) -> tuple[str, list[str]]:
        value = requested or self.default_language
        if value == "auto":
            value = "+".join(code for code in ("eng", "vie") if code in self.available_languages) or "eng"
        requested_codes = [code for code in value.split("+") if code in self.available_languages]
        warnings: list[str] = []
        if not requested_codes:
            requested_codes = ["eng"] if "eng" in self.available_languages else [next(iter(self.available_languages), "eng")]
            warnings.append(f"ocr_language_unavailable:{value}")
        elif len(requested_codes) != len(value.split("+")):
            warnings.append(f"ocr_language_partial:{value}")
        return "+".join(requested_codes), warnings

    def supports_language(self, language: str) -> bool:
        return all(code in self.available_languages for code in language.split("+"))

    def recognize(self, image: Any, page_number: int, language: str | None = None) -> OCRPageResult:
        lang, language_warnings = self.resolve_language(language)
        config = f"--oem 3 --psm {self.psm}"
        try:
            data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=Output.DICT)
        except pytesseract.TesseractError:
            lang = "eng" if "eng" in self.available_languages else lang.split("+")[0]
            data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=Output.DICT)
            language_warnings.append("ocr_engine_fallback_to_single_language")
        tokens: list[OCRToken] = []
        text_parts: list[str] = []
        for index, raw_text in enumerate(data.get("text", [])):
            text = str(raw_text or "").strip()
            try:
                confidence_value = float(data.get("conf", [0])[index]) / 100.0
            except (ValueError, TypeError, IndexError):
                confidence_value = 0.0
            if not text:
                continue
            left = float(data.get("left", [0])[index])
            top = float(data.get("top", [0])[index])
            width = float(data.get("width", [0])[index])
            height = float(data.get("height", [0])[index])
            tokens.append(OCRToken(
                text=text,
                bbox=BoundingBox(left, top, left + width, top + height),
                confidence=Confidence.from_score(confidence_value, self.name),
                line_number=int(data.get("line_num", [0])[index]),
                block_number=int(data.get("block_num", [0])[index]),
                page_number=page_number,
            ))
            text_parts.append(text)
        width, height = image.size[:2]
        return OCRPageResult(
            page_number=page_number,
            width=width,
            height=height,
            text=" ".join(text_parts),
            tokens=tokens,
            language=lang,
            engine=self.name,
            warnings=language_warnings,
        )
