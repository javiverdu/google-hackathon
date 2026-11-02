"""Review workflow: sidecars, approve/discard, status log, editable sheet and signing."""

from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfReader
from reportlab.pdfgen import canvas

import erasmus_agent.tools.status_log as status_log
from erasmus_agent.tools.excel_writer import (
    read_documents,
    read_students,
    upsert_student,
    write_students,
)
from erasmus_agent.tools.file_saver import (
    approve_review_item,
    discard_review_item,
    list_review_items,
    move_to_review,
    read_review_sidecar,
)
from erasmus_agent.tools.signature import render_typed_signature, stamp_signature_on_pdf
from erasmus_agent.tools.status_log import status_for
from tests.helpers import make_info


def blank_pdf(pages: int = 1) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    for _ in range(pages):
        pdf.drawString(100, 750, "Erasmus document")
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def test_review_sidecar_records_reason_and_guess(tmp_path):
    review = tmp_path / "review"
    info = make_info(confidence=0.32, notes="blurry scan")

    target = move_to_review(
        b"%PDF-1.4 scan",
        "scan_0042.pdf",
        review,
        reason="confidence=0.32",
        info=info,
        source_email="email_03.eml",
    )

    sidecar = read_review_sidecar(target)
    assert sidecar["reason"] == "confidence=0.32"
    assert sidecar["source_email"] == "email_03.eml"
    assert sidecar["original_name"] == "scan_0042.pdf"
    assert sidecar["extracted"]["student_surname"] == "Garcia"
    assert sidecar["extracted"]["doc_type"] == "LearningAgreement"


def test_list_review_items_ignores_sidecars(tmp_path):
    review = tmp_path / "review"
    move_to_review(b"a", "scan.pdf", review, reason="low confidence", info=make_info())

    items = list_review_items(review)
    assert [path.name for path in items] == ["scan.pdf"]


def test_approve_moves_document_and_clears_review(tmp_path):
    review = tmp_path / "review"
    out = tmp_path / "out"
    target = move_to_review(b"%PDF-1.4 scan", "scan.pdf", review, reason="low", info=make_info())

    saved = approve_review_item(target, make_info(), out)

    assert saved.parent == out
    assert saved.name == "Garcia_Ana_LearningAgreement_2026-27.pdf"
    assert saved.read_bytes() == b"%PDF-1.4 scan"
    assert list_review_items(review) == []
    assert not (review / "scan.pdf.reason.txt").exists()
    assert not (review / "scan.pdf.json").exists()


def test_discard_removes_document_and_sidecars(tmp_path):
    review = tmp_path / "review"
    target = move_to_review(b"a", "scan.pdf", review, reason="low", info=make_info())

    discard_review_item(target)

    assert list(review.iterdir()) == []


def test_status_log_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr(status_log, "LOG_PATH", tmp_path / "processing_log.json")

    assert status_for(None, has_attachments=True) == "new"
    assert status_for(None, has_attachments=False) == "question"

    status_log.record_run(
        "email_01.eml",
        "Learning Agreement",
        "ana@example.com",
        1,
        {"saved": ["Garcia_Ana_LearningAgreement_2026-27.pdf"], "review": [], "errors": []},
    )
    entry = status_log.read_log()["email_01.eml"]
    assert status_for(entry, True) == "processed"

    status_log.record_run(
        "email_02.eml",
        "Scan",
        "ana@example.com",
        1,
        {"saved": [], "review": ["scan.pdf"], "errors": []},
    )
    entry = status_log.read_log()["email_02.eml"]
    assert status_for(entry, True) == "needs_review"

    status_log.resolve_review_item("email_02.eml", "scan.pdf", "Garcia_Ana_Transcript_2026-27.pdf")
    entry = status_log.read_log()["email_02.eml"]
    assert entry["review"] == []
    assert entry["saved"] == ["Garcia_Ana_Transcript_2026-27.pdf"]
    assert status_for(entry, True) == "processed"


def test_write_students_keeps_documents_sheet(tmp_path):
    xlsx = tmp_path / "students.xlsx"
    upsert_student(xlsx, make_info(), saved_filename="Garcia_Ana_LearningAgreement_2026-27.pdf")

    rows = read_students(xlsx)
    rows[0]["HostUniversity"] = "University of Porto"
    write_students(xlsx, rows)

    assert read_students(xlsx)[0]["HostUniversity"] == "University of Porto"
    assert len(read_documents(xlsx)) == 1


def test_typed_signature_is_a_png():
    png = render_typed_signature("Ana Garcia")
    assert png.startswith(b"\x89PNG")
    assert len(png) > 500


def test_signature_is_stamped_on_the_pdf():
    pdf = blank_pdf()
    signature = render_typed_signature("Ana Garcia")

    signed = stamp_signature_on_pdf(pdf, signature, position="bottom-right")

    assert signed.startswith(b"%PDF")
    assert len(signed) > len(pdf)
    assert len(PdfReader(BytesIO(signed)).pages) == 1


@pytest.mark.parametrize("position", ["bottom-left", "bottom-center", "bottom-right"])
def test_signature_positions_are_accepted(position):
    signed = stamp_signature_on_pdf(blank_pdf(), render_typed_signature("Ana"), position=position)
    assert len(PdfReader(BytesIO(signed)).pages) == 1
