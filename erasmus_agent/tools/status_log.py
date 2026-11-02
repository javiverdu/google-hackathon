"""Tiny persisted index of what happened to each inbox email.

The pipeline writes renamed files to data/out/ and flagged ones to
data/review/, but neither folder remembers which *email* a file came from
once it's been approved. This log is the missing piece: it lets the UI show
a real New / Needs review / Processed status per email, even after a page
reload or after a human resolves a review item later.
"""

from __future__ import annotations

import json

from ..config import DATA_DIR

LOG_PATH = DATA_DIR / "processing_log.json"


def read_log() -> dict:
    if not LOG_PATH.exists():
        return {}
    return json.loads(LOG_PATH.read_text(encoding="utf-8"))


def write_log(log: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")


def record_run(source_email: str, subject: str, sender: str, attachments: int, result: dict) -> None:
    """Called once per email right after the pipeline processes it."""
    log = read_log()
    log[source_email] = {
        "subject": subject,
        "sender": sender,
        "attachments": attachments,
        "saved": result.get("saved", []),
        "review": result.get("review", []),
        "errors": result.get("errors", []),
        "documents": result.get("documents", []),
        "processed": True,
    }
    write_log(log)


def resolve_review_item(source_email: str, original_filename: str, saved_filename: str | None) -> None:
    """Called when a human approves or discards a document from the Review tab."""
    log = read_log()
    entry = log.get(source_email)
    if not entry:
        return
    entry["review"] = [name for name in entry.get("review", []) if name != original_filename]
    if saved_filename:
        entry.setdefault("saved", []).append(saved_filename)
    log[source_email] = entry
    write_log(log)


def status_for(entry: dict | None, has_attachments: bool) -> str:
    """New / question / needs_review / processed, in that priority order."""
    if not entry or not entry.get("processed"):
        return "question" if not has_attachments else "new"
    if entry.get("review"):
        return "needs_review"
    if not has_attachments:
        return "question"
    if entry.get("saved"):
        return "processed"
    return "new"
