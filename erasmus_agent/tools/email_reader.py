"""Read .eml files with the Python standard library (no extra dependency)."""

from __future__ import annotations

import email
import re
from collections.abc import Iterator
from email import policy
from pathlib import Path


def _html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def read_email(path: str | Path) -> dict:
    """Parse one .eml into a plain dict with body and attachments."""
    path = Path(path)
    message = email.message_from_bytes(path.read_bytes(), policy=policy.default)

    body_parts: list[str] = []
    attachments: list[dict] = []

    for part in message.walk():
        if part.is_multipart():
            continue
        disposition = (part.get_content_disposition() or "").lower()
        filename = part.get_filename()
        content_type = part.get_content_type()
        payload = part.get_payload(decode=True) or b""

        if disposition == "attachment" or filename:
            attachments.append(
                {
                    "name": filename or f"attachment_{len(attachments) + 1}",
                    "content_type": content_type,
                    "data": payload,
                }
            )
        elif content_type == "text/plain":
            body_parts.append(part.get_content())
        elif content_type == "text/html":
            body_parts.append(_html_to_text(part.get_content()))

    return {
        "path": str(path),
        "filename": path.name,
        "subject": str(message.get("subject", "")),
        "sender": str(message.get("from", "")),
        "date": str(message.get("date", "")),
        "body": "\n".join(part.strip() for part in body_parts if part).strip(),
        "attachments": attachments,
    }


def iter_inbox(inbox_dir: str | Path) -> Iterator[dict]:
    """Yield every .eml in a folder (case-insensitive), sorted by name."""
    folder = Path(inbox_dir)
    if not folder.is_dir():
        return
    paths = sorted(
        path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".eml"
    )
    for path in paths:
        try:
            yield read_email(path)
        except Exception as exc:  # one broken file must not kill the batch
            yield {
                "path": str(path),
                "filename": path.name,
                "subject": "",
                "sender": "",
                "date": "",
                "body": "",
                "attachments": [],
                "error": str(exc),
            }
