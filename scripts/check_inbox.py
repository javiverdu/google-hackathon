"""Inbox doctor: check emails before the demo, no Gemini call.

Usage:
    python scripts/check_inbox.py [folder]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from erasmus_agent.config import REVIEW_DIR  # noqa: E402
from erasmus_agent.tools.email_reader import iter_inbox  # noqa: E402

SUPPORTED = {"application/pdf", "image/png", "image/jpeg", "image/webp", "image/heic", "image/heif"}


def main(folder: str | None = None) -> int:
    inbox = Path(folder) if folder else Path(__file__).resolve().parent.parent / "data" / "inbox"
    if not inbox.is_dir():
        print(f"ERROR: inbox not found: {inbox}")
        return 1

    emails = list(iter_inbox(inbox))
    problems = 0
    print(f"Inbox: {inbox}")
    print(f"Emails: {len(emails)}\n")

    for meta in emails:
        warnings: list[str] = []
        if meta.get("error"):
            warnings.append(f"unreadable: {meta['error']}")
        if not meta["subject"]:
            warnings.append("no subject")
        if not meta["attachments"]:
            warnings.append("no attachments (will be skipped as a question)")
        for attachment in meta["attachments"]:
            name = attachment["name"]
            mime = attachment["content_type"]
            if mime not in SUPPORTED:
                warnings.append(f"{name}: unsupported type {mime} -> review")
            if not attachment["data"]:
                warnings.append(f"{name}: empty file -> review")
            if len(attachment["data"]) > 15 * 1024 * 1024:
                warnings.append(f"{name}: larger than 15 MB -> review")

        status = "OK" if not warnings else "WARN"
        if warnings:
            problems += 1
        print(f"[{status}] {meta['filename']} | {len(meta['attachments'])} attachments")
        for warning in warnings:
            print(f"       - {warning}")

    print(f"\nEmails with warnings: {problems}")
    print(f"Review folder: {REVIEW_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
