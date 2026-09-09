from __future__ import annotations

import re
from typing import Iterable, TypeVar

T = TypeVar("T")

_SPECIAL_RE = re.compile(r"[^\w\s]", re.UNICODE)
_VOWELS = set("aeiouàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ")


def is_noise_text(text: str, min_length: int = 6, special_ratio: float = 0.40) -> bool:
    """Detect seal/signature/watermark garbage without external models."""
    value = " ".join(str(text or "").split())
    if len(value) < min_length:
        return False
    non_space = [char for char in value if not char.isspace()]
    if not non_space:
        return True
    special = sum(bool(_SPECIAL_RE.match(char)) for char in non_space)
    if special / len(non_space) > special_ratio:
        return True
    letters = [char.casefold() for char in non_space if char.isalpha()]
    if len(letters) >= min_length:
        consonants = sum(char not in _VOWELS for char in letters)
        unique = len(set(letters))
        if consonants / len(letters) >= 0.85 and unique <= max(3, len(letters) // 2):
            return True
    return bool(re.fullmatch(r"([^\w\s])\1{2,}|(\w)\2{3,}", value, re.UNICODE))


def filter_text_lines(lines: Iterable[str]) -> list[str]:
    return [line for line in lines if not is_noise_text(line)]


def filter_blocks(blocks: Iterable[T]) -> list[T]:
    """Drop noisy objects and mark retained objects with a stable diagnostic flag."""
    retained: list[T] = []
    for block in blocks:
        if is_noise_text(getattr(block, "text", "")):
            attributes = getattr(block, "attributes", None)
            if isinstance(attributes, dict):
                attributes["is_noise"] = True
            continue
        attributes = getattr(block, "attributes", None)
        if isinstance(attributes, dict):
            attributes["is_noise"] = False
        retained.append(block)
    return retained
