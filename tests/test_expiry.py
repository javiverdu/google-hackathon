"""Dates: expired documents must be flagged, invalid dates must not crash."""

from __future__ import annotations

from datetime import date

from erasmus_agent.schemas import DocType, is_expired
from erasmus_agent.tools.excel_writer import read_documents, read_students, upsert_student
from tests.helpers import make_info

TODAY = date(2026, 11, 2)


def test_is_expired_rules():
    assert is_expired("2026-01-01", TODAY) is True
    assert is_expired("2026-12-31", TODAY) is False
    assert is_expired("2026-11-02", TODAY) is False
    assert is_expired("", TODAY) is False
    assert is_expired("not-a-date", TODAY) is False
    assert is_expired("2026-13-40", TODAY) is False


def test_expired_insurance_is_flagged(tmp_path):
    xlsx = tmp_path / "students.xlsx"
    upsert_student(
        xlsx,
        make_info(
            doc_type=DocType.insurance,
            start_date="2025-09-01",
            end_date="2026-06-30",
        ),
        saved_filename="Garcia_Ana_Insurance_2025-26.pdf",
        today=TODAY,
    )
    row = read_students(xlsx)[0]
    assert row["Expired"] == "Insurance"


def test_valid_insurance_is_not_flagged(tmp_path):
    xlsx = tmp_path / "students.xlsx"
    upsert_student(
        xlsx,
        make_info(doc_type=DocType.insurance, end_date="2027-06-30"),
        saved_filename="Garcia_Ana_Insurance_2026-27.pdf",
        today=TODAY,
    )
    assert read_students(xlsx)[0]["Expired"] == "-"


def test_updating_document_clears_expired_flag(tmp_path):
    xlsx = tmp_path / "students.xlsx"
    filename = "Garcia_Ana_Insurance_2026-27.pdf"
    upsert_student(
        xlsx,
        make_info(doc_type=DocType.insurance, end_date="2026-01-01"),
        saved_filename=filename,
        today=TODAY,
    )
    assert read_students(xlsx)[0]["Expired"] == "Insurance"

    upsert_student(
        xlsx,
        make_info(doc_type=DocType.insurance, end_date="2027-12-31"),
        saved_filename=filename,
        today=TODAY,
    )
    assert read_students(xlsx)[0]["Expired"] == "-"


def test_invalid_end_date_does_not_break_the_row(tmp_path):
    xlsx = tmp_path / "students.xlsx"
    upsert_student(
        xlsx,
        make_info(doc_type=DocType.insurance, end_date="sometime in 2027"),
        saved_filename="scan.pdf",
        today=TODAY,
    )
    assert read_students(xlsx)[0]["Expired"] == "-"


def test_documents_detail_sheet_has_one_row_per_file(tmp_path):
    xlsx = tmp_path / "students.xlsx"
    upsert_student(xlsx, make_info(), saved_filename="la.pdf", today=TODAY)
    upsert_student(
        xlsx,
        make_info(doc_type=DocType.transcript, end_date="2027-01-01"),
        saved_filename="transcript.pdf",
        today=TODAY,
    )
    documents = read_documents(xlsx)
    assert len(documents) == 2
    assert {row["Filename"] for row in documents} == {"la.pdf", "transcript.pdf"}
    assert len(read_students(xlsx)) == 1


def test_review_without_filename_does_not_create_detail_row(tmp_path):
    xlsx = tmp_path / "students.xlsx"
    upsert_student(xlsx, make_info(student_surname="", confidence=0.1), status="needs_review", today=TODAY)
    assert read_documents(xlsx) == []
