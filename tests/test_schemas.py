"""Naming and semester rules must stay stable across the whole team."""

from erasmus_agent.schemas import DocType, DocumentInfo, build_filename, semester_tag, slug


def test_slug_removes_accents_and_spaces():
    assert slug("Núñez") == "Nunez"
    assert slug("Garcia Lopez") == "GarciaLopez"
    assert slug("") == "Unknown"


def test_semester_variants():
    assert semester_tag("2026-27") == "2026-27"
    assert semester_tag("2026/2027") == "2026-27"
    assert semester_tag("26-27") == "2026-27"


def test_filename_pattern():
    info = DocumentInfo(
        student_first_name="Ana",
        student_surname="García López",
        doc_type=DocType.learning_agreement,
        semester="2026/2027",
    )
    assert build_filename(info) == "GarciaLopez_Ana_LearningAgreement_2026-27.pdf"


def test_filename_keeps_original_extension():
    info = DocumentInfo(
        student_first_name="Maria",
        student_surname="Rossi",
        doc_type=DocType.insurance,
        semester="2026-27",
    )
    assert build_filename(info, ".JPG") == "Rossi_Maria_Insurance_2026-27.jpg"
