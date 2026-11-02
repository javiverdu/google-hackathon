"""ADK tool functions. Keep signatures stable: the whole team codes against them."""

from __future__ import annotations

from pathlib import Path

from ..config import FAQ_FILE, INBOX_DIR, OUT_DIR, SPREADSHEET
from ..schemas import build_filename
from .email_reader import iter_inbox, read_email
from .excel_writer import read_students, upsert_student
from .faq import load_faq, search_faq
from .file_saver import move_to_review, save_document

__all__ = [
    "iter_inbox",
    "read_email",
    "read_students",
    "upsert_student",
    "load_faq",
    "search_faq",
    "move_to_review",
    "save_document",
    "build_filename",
    "INBOX_DIR",
    "OUT_DIR",
    "SPREADSHEET",
    "FAQ_FILE",
    "Path",
]
