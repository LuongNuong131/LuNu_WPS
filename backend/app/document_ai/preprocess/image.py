from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageFilter, ImageOps


@dataclass
class PreprocessedImage:
    image: Image.Image
    profile: str
    warnings: list[str]


def prepare_for_ocr(image: Image.Image, profile: str = "adaptive") -> PreprocessedImage:
    warnings: list[str] = []
    work = image.convert("L")
    if profile in {"adaptive", "contrast"}:
        work = ImageOps.autocontrast(work, cutoff=1)
    if profile in {"adaptive", "denoise"}:
        work = work.filter(ImageFilter.MedianFilter(size=3))
    if profile in {"adaptive", "threshold"}:
        work = work.point(lambda value: 255 if value > 180 else 0)
    if profile in {"adaptive", "contrast", "denoise", "threshold"}:
        work = work.resize((work.width * 2, work.height * 2), Image.Resampling.LANCZOS)
    if work.width < 800:
        warnings.append("low_resolution_input")
    return PreprocessedImage(work, profile, warnings)


def image_quality(image: Image.Image) -> dict[str, Any]:
    grayscale = ImageOps.grayscale(image)
    histogram = grayscale.histogram()
    total = max(1, sum(histogram))
    mean = sum(index * count for index, count in enumerate(histogram)) / total
    dark_ratio = sum(histogram[:40]) / total
    bright_ratio = sum(histogram[220:]) / total
    return {
        "width": image.width,
        "height": image.height,
        "pixels": image.width * image.height,
        "mean_luminance": round(mean, 2),
        "dark_ratio": round(dark_ratio, 3),
        "bright_ratio": round(bright_ratio, 3),
        "low_contrast": bright_ratio > 0.92 or dark_ratio > 0.92,
    }
