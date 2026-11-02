"""Questions the agent cannot answer go to a real person, with an audit trail."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from ..config import ESCALATIONS

HEADERS = ["timestamp", "student", "question", "reason"]


def log_escalation(
    question: str,
    reason: str = "not covered by the FAQ",
    student: str = "",
    path: str | Path | None = None,
) -> Path:
    """Append one handoff row and return the CSV path."""
    target = Path(path) if path else ESCALATIONS
    target.parent.mkdir(parents=True, exist_ok=True)
    is_new = not target.exists() or target.stat().st_size == 0
    with target.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if is_new:
            writer.writerow(HEADERS)
        writer.writerow(
            [
                datetime.now(UTC).isoformat(timespec="seconds"),
                student.strip(),
                " ".join((question or "").split()),
                " ".join((reason or "").split()),
            ]
        )
    return target


def read_escalations(path: str | Path | None = None) -> list[dict]:
    target = Path(path) if path else ESCALATIONS
    if not target.exists():
        return []
    with target.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]
