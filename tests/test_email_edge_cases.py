"""Broken, weird and hostile emails must never crash the inbox reader."""

from __future__ import annotations

from pathlib import Path

from erasmus_agent.tools.email_reader import iter_inbox, read_email
from erasmus_agent.tools.file_saver import move_to_review, save_document
from tests.helpers import make_email, make_info


def test_empty_file_is_reported_without_crashing(inbox):
    (inbox / "empty.eml").write_bytes(b"")
    emails = list(iter_inbox(inbox))
    assert len(emails) == 1
    assert emails[0]["attachments"] == []


def test_garbage_bytes_do_not_crash(inbox):
    (inbox / "garbage.eml").write_bytes(b"\x00\xff\xfe not an email at all")
    emails = list(iter_inbox(inbox))
    assert len(emails) == 1
    assert emails[0]["filename"] == "garbage.eml"


def test_uppercase_extension_is_discovered(inbox):
    make_email(inbox / "EMAIL_01.EML", attachments=[{"filename": "scan.pdf"}])
    emails = list(iter_inbox(inbox))
    assert [meta["filename"] for meta in emails] == ["EMAIL_01.EML"]


def test_other_extensions_are_ignored(inbox):
    (inbox / "notes.txt").write_text("hello", encoding="utf-8")
    (inbox / "message.emlx").write_bytes(b"x")
    assert list(iter_inbox(inbox)) == []


def test_html_only_email_gets_text_body(inbox):
    path = make_email(
        inbox / "html.eml",
        body="",
        html="<html><body><p>My insurance is attached</p></body></html>",
    )
    meta = read_email(path)
    assert "insurance" in meta["body"].lower()


def test_email_without_subject_or_sender(inbox):
    path = make_email(inbox / "bare.eml", subject="", sender="")
    meta = read_email(path)
    assert meta["subject"] == ""
    assert meta["sender"] == ""


def test_attachment_without_filename_gets_placeholder(inbox):
    path = make_email(
        inbox / "noname.eml",
        attachments=[{"filename": None, "data": b"%PDF-1.4 anonymous"}],
    )
    meta = read_email(path)
    assert len(meta["attachments"]) == 1
    assert meta["attachments"][0]["name"].startswith("attachment_")


def test_unicode_attachment_filename_is_kept(inbox):
    path = make_email(
        inbox / "unicode.eml",
        attachments=[{"filename": "certificado_ñandú.pdf", "data": b"%PDF-1.4"}],
    )
    meta = read_email(path)
    name = meta["attachments"][0]["name"]
    assert name.lower().endswith(".pdf")
    assert "and" in name.lower()


def test_review_name_cannot_escape_folder(tmp_path):
    review = tmp_path / "review"
    target = move_to_review(b"x", "..\\..\\evil.pdf", review, reason="test")
    assert target.parent == review
    assert "\\" not in target.name
    assert target.exists()


def test_review_collision_gets_counter(tmp_path):
    review = tmp_path / "review"
    first = move_to_review(b"a", "scan.pdf", review)
    second = move_to_review(b"b", "scan.pdf", review)
    assert first.name == "scan.pdf"
    assert second.name == "scan-2.pdf"


def test_review_same_content_is_not_duplicated(tmp_path):
    review = tmp_path / "review"
    first = move_to_review(b"same", "scan.pdf", review, reason="confidence=0.20")
    second = move_to_review(b"same", "scan.pdf", review, reason="confidence=0.20")

    assert second == first
    assert [path.name for path in review.iterdir() if not path.name.endswith(".reason.txt")] == [
        "scan.pdf"
    ]
    reason = review / "scan.pdf.reason.txt"
    assert reason.read_text() == "confidence=0.20"


def test_very_long_names_are_truncated(tmp_path):
    info = make_info(student_surname="Lopez " * 60, student_first_name="Ana " * 40)
    target = save_document(b"%PDF-1.4", "scan.pdf", info, tmp_path)
    assert len(target.name) <= 120
    assert target.name.endswith(".pdf")


def test_save_collision_keeps_both_files(tmp_path):
    info = make_info()
    first = save_document(b"a", "scan.pdf", info, tmp_path)
    second = save_document(b"b", "scan.pdf", info, tmp_path)
    assert first.name == "Garcia_Ana_LearningAgreement_2026-27.pdf"
    assert second.name == "Garcia_Ana_LearningAgreement_2026-27-2.pdf"
    assert first.read_bytes() != second.read_bytes()


def test_read_email_accepts_pathlib_and_str(inbox):
    path = make_email(inbox / "path.eml")
    assert read_email(path)["filename"] == "path.eml"
    assert read_email(str(path))["filename"] == "path.eml"


def test_missing_inbox_folder_yields_nothing(tmp_path):
    assert list(iter_inbox(Path(tmp_path) / "does-not-exist")) == []
