"""Emails uploaded from the web UI are stored safely and deduplicated."""

from __future__ import annotations

from email.message import EmailMessage

from erasmus_agent.tools.email_reader import iter_inbox, read_email
from erasmus_agent.tools.inbox_store import (
    compose_email,
    store_email_bytes,
    student_submission_email,
)


def make_raw_email(subject: str = "Docs", body: str = "Hello") -> bytes:
    message = EmailMessage()
    message["From"] = "student@example.com"
    message["To"] = "erasmus@example.edu"
    message["Subject"] = subject
    message.set_content(body)
    return bytes(message)


def test_store_creates_file(tmp_path):
    name, created = store_email_bytes("my_email.eml", make_raw_email(), tmp_path)
    assert created is True
    assert name == "my_email.eml"
    assert (tmp_path / name).exists()


def test_identical_upload_is_deduplicated(tmp_path):
    data = make_raw_email()
    first, created_first = store_email_bytes("a.eml", data, tmp_path)
    second, created_second = store_email_bytes("b.eml", data, tmp_path)
    assert created_first is True
    assert created_second is False
    assert second == first
    assert len(list(tmp_path.glob("*.eml"))) == 1


def test_different_uploads_with_same_name_get_counter(tmp_path):
    first, _ = store_email_bytes("email.eml", make_raw_email("one"), tmp_path)
    second, _ = store_email_bytes("email.eml", make_raw_email("two"), tmp_path)
    assert first == "email.eml"
    assert second == "email-2.eml"


def test_unsafe_name_is_sanitised(tmp_path):
    name, _ = store_email_bytes("../../evil name.eml", make_raw_email(), tmp_path)
    assert "/" not in name
    assert "\\" not in name
    assert (tmp_path / name).exists()


def test_missing_extension_is_added(tmp_path):
    name, _ = store_email_bytes("message", make_raw_email(), tmp_path)
    assert name == "message.eml"


def test_compose_email_roundtrip(tmp_path):
    data = compose_email(
        subject="Insurance",
        sender="maria@example.com",
        body="Please find my insurance attached.",
        attachments=[
            {"filename": "insurance.pdf", "data": b"%PDF-1.4 fake", "content_type": "application/pdf"}
        ],
    )
    path = tmp_path / "composed.eml"
    path.write_bytes(data)

    meta = read_email(path)
    assert meta["subject"] == "Insurance"
    assert meta["sender"] == "maria@example.com"
    assert len(meta["attachments"]) == 1
    assert meta["attachments"][0]["name"] == "insurance.pdf"


def test_composed_email_is_read_by_iter_inbox(tmp_path):
    path = tmp_path / "one.eml"
    path.write_bytes(compose_email("Deadline", "student@example.com", "When is it?"))
    emails = list(iter_inbox(tmp_path))
    assert len(emails) == 1
    assert emails[0]["subject"] == "Deadline"


def test_student_form_builds_structured_email(tmp_path):
    data = student_submission_email(
        first_name="Ana",
        surname="Garcia",
        email="ana@example.com",
        semester="2026-27",
        host_university="University of Bologna",
        doc_type="LearningAgreement",
        start_date="2026-09-01",
        end_date="2027-02-28",
        deadline="2026-10-15",
        message="Here is my signed agreement.",
        attachment={
            "filename": "scan_0042.pdf",
            "data": b"%PDF-1.4 fake",
            "content_type": "application/pdf",
        },
    )
    path = tmp_path / "form.eml"
    path.write_bytes(data)
    meta = read_email(path)

    assert meta["subject"] == "LearningAgreement - Ana Garcia"
    assert meta["sender"] == "ana@example.com"
    assert "Student surname: Garcia" in meta["body"]
    assert "Host university: University of Bologna" in meta["body"]
    assert "Deadline: 2026-10-15" in meta["body"]
    assert len(meta["attachments"]) == 1
    assert meta["attachments"][0]["name"] == "scan_0042.pdf"


def test_student_form_without_attachment_is_a_question(tmp_path):
    data = student_submission_email(
        first_name="Tomas",
        surname="Ferreira",
        email="tomas@example.com",
        semester="2026-27",
        host_university="University of Porto",
        doc_type="Other",
        message="When is the deadline?",
    )
    path = tmp_path / "question.eml"
    path.write_bytes(data)
    meta = read_email(path)

    assert meta["attachments"] == []
    assert "When is the deadline?" in meta["body"]
    assert meta["subject"] == "Other - Tomas Ferreira"
