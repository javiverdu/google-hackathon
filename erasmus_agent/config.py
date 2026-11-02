"""Central configuration. Works on Windows and Linux (pathlib only)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("ERASMUS_DATA_DIR", PROJECT_ROOT / "data")).resolve()
INBOX_DIR = DATA_DIR / "inbox"
OUT_DIR = DATA_DIR / "out"
REVIEW_DIR = DATA_DIR / "review"
SPREADSHEET = DATA_DIR / "students.xlsx"
FAQ_FILE = PROJECT_ROOT / "faq.md"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_FALLBACK_MODELS = [
    model.strip()
    for model in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-3.8-flash,gemini-3.5-flash-lite,gemini-flash-latest,gemini-3.1-flash-lite",
    ).split(",")
    if model.strip()
]
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
MAX_ATTACHMENT_BYTES = int(float(os.getenv("MAX_ATTACHMENT_MB", "15")) * 1024 * 1024)
SEMESTER = os.getenv("ERASMUS_SEMESTER", "2026-27")

for _folder in (DATA_DIR, INBOX_DIR, OUT_DIR, REVIEW_DIR):
    _folder.mkdir(parents=True, exist_ok=True)


def api_key() -> str:
    """Return the Gemini key from env or Streamlit secrets."""
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        try:  # Streamlit Community Cloud exposes secrets this way
            import streamlit as st

            key = st.secrets.get("GOOGLE_API_KEY")  # type: ignore[union-attr]
        except Exception:
            key = None
    if not key:
        raise RuntimeError(
            "GOOGLE_API_KEY missing. Copy .env.example to .env and add your AI Studio key."
        )
    return key
