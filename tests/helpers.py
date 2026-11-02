"""Helpers to build synthetic emails and classifications."""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

from erasmus_agent.schemas import DocType, DocumentInfo


def make_email(
    path: Path,
    subject: str = "Documents",
    body: str = "Hello, attached are my documents.",
    sender: str = "student@example.com",
    attachments: list[dict] | None = None,
    html: str | None = None,
) -> Path:
    """attachments: [{'filename': 'x.pdf', 'data': b'...', 'maintype': 'application', 'subtype': 'pdf'}]"""
    message = EmailMessage()
    if sender:
        message["From"] = sender
    message["To"] = "erasmus@example.edu"
    if subject:
        message["Subject"] = subject
    message.set_content(body)
    if html:
        message.add_alternative(html, subtype="html")

    for item in attachments or []:
        message.add_attachment(
            item.get("data", b"%PDF-1.4 fake"),
            maintype=item.get("maintype", "application"),
            subtype=item.get("subtype", "pdf"),
            filename=item.get("filename"),
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(message))
    return path


def make_info(**overrides) -> DocumentInfo:
    values = {
        "student_first_name": "Ana",
        "student_surname": "Garcia",
        "doc_type": DocType.learning_agreement,
        "semester": "2026-27",
        "host_university": "University of Bologna",
        "start_date": "2026-09-01",
        "end_date": "2027-02-28",
        "deadline": "2026-10-15",
        "confidence": 0.95,
    }
    values.update(overrides)
    return DocumentInfo(**values)
