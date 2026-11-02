"""Accept emails from the web UI and store them as .eml files."""

from __future__ import annotations

import mimetypes
import re
from email.message import EmailMessage
from pathlib import Path

_UNSAFE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _safe_name(name: str, fallback: str = "email") -> str:
    cleaned = _UNSAFE.sub("_", Path(name or "").name).strip(" .") or fallback
    if not cleaned.lower().endswith(".eml"):
        cleaned += ".eml"
    return cleaned[:120]


def store_email_bytes(
    name: str,
    data: bytes,
    inbox_dir: str | Path,
) -> tuple[str, bool]:
    """Save an uploaded .eml. Returns (filename, created).

    Identical content already in the inbox is not duplicated, so Streamlit
    reruns and repeated uploads are harmless.
    """
    folder = Path(inbox_dir)
    folder.mkdir(parents=True, exist_ok=True)

    for existing in folder.glob("*.eml"):
        try:
            if existing.read_bytes() == data:
                return existing.name, False
        except OSError:
            continue

    base = _safe_name(name)
    target = folder / base
    counter = 2
    while target.exists():
        target = folder / f"{Path(base).stem}-{counter}.eml"
        counter += 1
    target.write_bytes(data)
    return target.name, True


def compose_email(
    subject: str,
    sender: str,
    body: str,
    attachments: list[dict] | None = None,
) -> bytes:
    """Build a valid .eml from a small web form."""
    message = EmailMessage()
    message["From"] = sender or "student@example.com"
    message["To"] = "erasmus@example.edu"
    message["Subject"] = subject or "Documents"
    message.set_content(body or "Please find my documents attached.")

    for item in attachments or []:
        filename = item.get("filename") or "attachment"
        ctype = item.get("content_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        maintype, _, subtype = ctype.partition("/")
        message.add_attachment(
            item["data"],
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=filename,
        )
    return bytes(message)
