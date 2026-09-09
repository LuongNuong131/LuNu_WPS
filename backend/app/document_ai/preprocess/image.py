from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps


@dataclass
class PreprocessedImage:
    image: Image.Image
    profile: str
    warnings: list[str]
    deskew_angle: float = 0.0
    diagnostics: dict[str, Any] | None = None


def _deskew(image: Image.Image) -> tuple[Image.Image, float, list[str]]:
    """Estimate the dominant text-line angle and rotate only when evidence is strong."""
    warnings: list[str] = []
    gray = np.asarray(ImageOps.grayscale(image))
    if gray.size == 0:
        return image, 0.0, ["empty_image"]
    binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    points = cv2.findNonZero(binary)
    if points is None or len(points) < 40:
        return image, 0.0, ["deskew_insufficient_signal"]
    angle = float(cv2.minAreaRect(points)[-1])
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.35 or abs(angle) > 12:
        return image, 0.0, warnings
    height, width = gray.shape
    center = (width / 2.0, height / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(gray, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(rotated), round(angle, 3), warnings


def prepare_for_ocr(image: Image.Image, profile: str = "adaptive") -> PreprocessedImage:
    warnings: list[str] = []
    work = image.convert("L")
    angle = 0.0
    if profile in {"adaptive", "contrast", "deskew", "denoise", "threshold"}:
        work, angle, deskew_warnings = _deskew(work)
        warnings.extend(deskew_warnings)
    if profile in {"adaptive", "contrast"}:
        work = ImageOps.autocontrast(work, cutoff=1)
    if profile in {"adaptive", "denoise"}:
        work = work.filter(ImageFilter.MedianFilter(size=3))
    if profile in {"adaptive", "threshold"}:
        work = work.point(lambda value: 255 if value > 180 else 0)
    if profile in {"adaptive", "contrast", "denoise", "threshold", "deskew"}:
        work = work.resize((work.width * 2, work.height * 2), Image.Resampling.LANCZOS)
    if work.width < 800:
        warnings.append("low_resolution_input")
    return PreprocessedImage(work, profile, warnings, angle, {"deskew_applied": bool(angle), "deskew_angle": angle})


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
