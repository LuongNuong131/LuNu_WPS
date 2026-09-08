from __future__ import annotations

import re
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
        candidates: list[OCRPageResult] = []
        for psm in (self.psm, 11) if self.psm != 11 else (11, 6):
            try:
                candidates.append(self._recognize_pass(image, page_number, lang, psm, language_warnings))
            except pytesseract.TesseractError:
                fallback_lang = "eng" if "eng" in self.available_languages else lang.split("+")[0]
                if fallback_lang != lang:
                    language_warnings.append("ocr_engine_fallback_to_single_language")
                    candidates.append(self._recognize_pass(image, page_number, fallback_lang, psm, language_warnings))
        if not candidates:
            return OCRPageResult(page_number, image.size[0], image.size[1], "", language=lang, engine=self.name, warnings=[*language_warnings, "ocr_no_result"])
        scored = [(self._quality_score(candidate), candidate) for candidate in candidates]
        best_score, best = max(scored, key=lambda item: item[0])
        best.selected_pass = int(best.diagnostics.get("psm", self.psm))
        best.pass_scores = {str(candidate.diagnostics.get("psm")): round(score, 4) for score, candidate in scored}
        best.diagnostics.update({"selected_score": round(best_score, 4), "passes_attempted": sorted(best.pass_scores)})
        return best

    def _recognize_pass(self, image: Any, page_number: int, lang: str, psm: int, warnings: list[str]) -> OCRPageResult:
        config = f"--oem 3 --psm {psm}"
        data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=Output.DICT)
        tokens: list[OCRToken] = []
        text_parts: list[str] = []
        for index, raw_text in enumerate(data.get("text", [])):
            text = str(raw_text or "").strip()
            try:
                confidence_value = max(0.0, float(data.get("conf", [0])[index]) / 100.0)
            except (ValueError, TypeError, IndexError):
                confidence_value = 0.0
            if not text:
                continue
            left = float(data.get("left", [0])[index])
            top = float(data.get("top", [0])[index])
            width = float(data.get("width", [0])[index])
            height = float(data.get("height", [0])[index])
            tokens.append(
                OCRToken(
                    text=text,
                    bbox=BoundingBox(left, top, left + width, top + height),
                    confidence=Confidence.from_score(confidence_value, self.name),
                    line_number=int(data.get("line_num", [0])[index]),
                    block_number=int(data.get("block_num", [0])[index]),
                    page_number=page_number,
                )
            )
            text_parts.append(text)
        return OCRPageResult(
            page_number=page_number,
            width=image.size[0],
            height=image.size[1],
            text=" ".join(text_parts),
            tokens=tokens,
            language=lang,
            engine=self.name,
            warnings=list(warnings),
            diagnostics={"psm": psm, "token_count": len(tokens)},
        )

    @staticmethod
    def _quality_score(result: OCRPageResult) -> float:
        if not result.tokens:
            return 0.0
        chars = "".join(token.text for token in result.tokens)
        alnum_ratio = sum(char.isalnum() for char in chars) / max(1, len(chars))
        meaningful = sum(1 for token in result.tokens if re.search(r"[A-Za-zÀ-ỹ0-9]", token.text))
        confidence = result.average_confidence or 0.0
        return (confidence * 0.55) + (alnum_ratio * 0.25) + (min(1.0, meaningful / 30) * 0.20)
