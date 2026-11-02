"""FAQ lookup. The LLM grounds answers on this file instead of inventing facts."""

from __future__ import annotations

import re
from pathlib import Path

from ..config import FAQ_FILE


def load_faq(path: str | Path | None = None) -> str:
    file = Path(path) if path else FAQ_FILE
    return file.read_text(encoding="utf-8") if file.exists() else ""


def search_faq(question: str, faq_text: str | None = None, top_k: int = 3) -> str:
    """Cheap keyword overlap, enough for a short FAQ in a hackathon demo."""
    faq_text = faq_text if faq_text is not None else load_faq()
    blocks = [block.strip() for block in re.split(r"\n(?=## )", faq_text) if block.strip()]
    words = set(re.findall(r"[a-z]{3,}", question.lower()))
    scored = []
    for block in blocks:
        overlap = len(words & set(re.findall(r"[a-z]{3,}", block.lower())))
        if overlap:
            scored.append((overlap, block))
    scored.sort(key=lambda item: item[0], reverse=True)
    return "\n\n".join(block for _, block in scored[:top_k])
