"""FAQ retrieval and spreadsheet rules."""

from __future__ import annotations

from erasmus_agent.schemas import DocType
from erasmus_agent.tools.excel_writer import read_students, upsert_student
from erasmus_agent.tools.faq import load_faq, search_faq
from tests.helpers import make_info


def test_faq_contains_expected_topics():
    faq = load_faq()
    assert "deadline" in faq.lower()
    assert "insurance" in faq.lower()
    assert "Learning Agreement" in faq


def test_search_faq_finds_insurance_block():
    result = search_faq("Did you receive my insurance certificate?")
    assert "insurance" in result.lower()


def test_search_faq_returns_empty_for_unknown_topic():
    assert search_faq("Can I bring my dog to the host university?") == ""


def test_excel_creates_headers_and_row(tmp_path):
    xlsx = tmp_path / "students.xlsx"
    upsert_student(xlsx, make_info(), saved_filename="Garcia_Ana_LearningAgreement_2026-27.pdf")

    rows = read_students(xlsx)
    assert len(rows) == 1
    assert rows[0]["Student"] == "Ana"
    assert "LearningAgreement" in rows[0]["Documents"]


def test_excel_does_not_duplicate_same_document(tmp_path):
    xlsx = tmp_path / "students.xlsx"
    info = make_info()
    upsert_student(xlsx, info, saved_filename="Garcia_Ana_LearningAgreement_2026-27.pdf")
    upsert_student(xlsx, info, saved_filename="Garcia_Ana_LearningAgreement_2026-27.pdf")

    row = read_students(xlsx)[0]
    assert row["Documents"].count("LearningAgreement") == 1


def test_excel_missing_list_updates_when_document_arrives(tmp_path):
    xlsx = tmp_path / "students.xlsx"
    upsert_student(
        xlsx,
        make_info(),
        saved_filename="Garcia_Ana_LearningAgreement_2026-27.pdf",
    )
    assert "Insurance" in read_students(xlsx)[0]["Missing"]

    upsert_student(
        xlsx,
        make_info(doc_type=DocType.insurance, host_university=""),
        saved_filename="Garcia_Ana_Insurance_2026-27.jpg",
    )
    row = read_students(xlsx)[0]
    assert "Insurance" not in row["Missing"]
    assert "LearningAgreement" not in row["Missing"]


def test_excel_keeps_existing_values_when_new_document_has_blanks(tmp_path):
    xlsx = tmp_path / "students.xlsx"
    upsert_student(xlsx, make_info(), saved_filename="a.pdf")
    upsert_student(
        xlsx,
        make_info(doc_type=DocType.transcript, host_university="", start_date="", end_date=""),
        saved_filename="b.pdf",
    )

    row = read_students(xlsx)[0]
    assert row["HostUniversity"] == "University of Bologna"
    assert row["StartDate"] == "2026-09-01"


def test_read_students_on_missing_file_returns_empty(tmp_path):
    assert read_students(tmp_path / "nope.xlsx") == []
