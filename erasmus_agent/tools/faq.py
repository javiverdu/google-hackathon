"""FAQ lookup. The LLM grounds answers on this file instead of inventing facts."""

from __future__ import annotations

import re
from pathlib import Path

from ..config import FAQ_FILE

STOPWORDS = {
    "the", "and", "for", "are", "can", "you", "your", "youre", "did", "does", "have",
    "has", "was", "were", "what", "when", "where", "who", "why", "how", "with", "from",
    "this", "that", "these", "those", "there", "their", "them", "then", "than", "into",
    "about", "after", "before", "should", "would", "could", "will", "shall", "may",
    "might", "must", "need", "needs", "please", "hello", "dear", "thank", "thanks",
    "regards", "best", "kind", "much", "very", "any", "all", "some", "not", "but",
    "our", "out", "get", "got", "send", "sent", "received", "receive", "still",
    "host", "university", "student", "students", "office", "erasmus", "question",
}


def load_faq(path: str | Path | None = None) -> str:
    file = Path(path) if path else FAQ_FILE
    return file.read_text(encoding="utf-8") if file.exists() else ""


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-z]{3,}", text.lower())
    return {word.rstrip("s") for word in words if word not in STOPWORDS}


def search_faq(question: str, faq_text: str | None = None, top_k: int = 3) -> str:
    """Keyword overlap with stopwords removed. Empty result means 'not covered'."""
    faq_text = faq_text if faq_text is not None else load_faq()
    blocks = [block.strip() for block in re.split(r"\n(?=## )", faq_text) if block.strip()]
    words = _terms(question)
    if not words:
        return ""

    scored: list[tuple[int, str]] = []
    for block in blocks:
        overlap = len(words & _terms(block))
        if overlap:
            scored.append((overlap, block))
    scored.sort(key=lambda item: item[0], reverse=True)
    return "\n\n".join(block for _, block in scored[:top_k])
