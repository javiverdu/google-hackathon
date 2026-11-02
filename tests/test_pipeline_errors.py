"""End-to-end pipeline with the LLM mocked: every failure path must be handled."""

from __future__ import annotations

from erasmus_agent.schemas import DocType, DocumentInfo
from erasmus_agent.tools.excel_writer import read_students
from tests.helpers import make_email, make_info


def _patch_classifier(monkeypatch, env, result):
    def fake(meta, attachment):
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(env.pipeline.llm, "classify_document", fake)


def test_email_without_attachment_is_skipped_not_an_error(inbox, env, monkeypatch):
    make_email(inbox / "question.eml", subject="Deadline?", body="When is the deadline?")
    called = {"count": 0}

    def fake(meta, attachment):
        called["count"] += 1
        return make_info()

    monkeypatch.setattr(env.pipeline.llm, "classify_document", fake)
    report = env.pipeline.run_inbox(inbox)

    assert report["emails"] == 1
    assert report["skipped"] == 1
    assert report["errors"] == 0
    assert called["count"] == 0


def test_unsupported_attachment_goes_to_review(inbox, env):
    make_email(
        inbox / "word.eml",
        attachments=[
            {
                "filename": "letter.docx",
                "data": b"PK fake docx",
                "maintype": "application",
                "subtype": "vnd.openxmlformats-officedocument.wordprocessingml.document",
            }
        ],
    )
    report = env.pipeline.run_inbox(inbox)

    assert report["saved"] == 0
    assert report["review"] == 1
    assert "Unsupported attachment type" in report["results"][0]["errors"][0]
    assert (env.review / "letter.docx").exists()


def test_running_inbox_twice_does_not_duplicate_review(inbox, env, monkeypatch):
    make_email(inbox / "blurry.eml", attachments=[{"filename": "foto_borrosa.jpg"}])
    _patch_classifier(monkeypatch, env, make_info(confidence=0.2))

    first = env.pipeline.run_inbox(inbox)
    second = env.pipeline.run_inbox(inbox)

    assert first["review"] == second["review"] == 1
    review_docs = [
        path
        for path in env.review.iterdir()
        if not path.name.endswith(".reason.txt") and path.suffix != ".json"
    ]
    assert [path.name for path in review_docs] == ["foto_borrosa.jpg"]
    assert len(read_students(env.xlsx)) == 1


def test_classifier_exception_goes_to_review(inbox, env, monkeypatch):
    make_email(inbox / "scan.eml", attachments=[{"filename": "scan_0042.pdf"}])
    _patch_classifier(monkeypatch, env, RuntimeError("503 model overloaded"))
    report = env.pipeline.run_inbox(inbox)

    assert report["saved"] == 0
    assert report["review"] == 1
    assert "503 model overloaded" in report["results"][0]["errors"][0]
    assert (env.review / "scan_0042.pdf.reason.txt").exists()


def test_low_confidence_review_does_not_guess_dates(inbox, env, monkeypatch):
    make_email(inbox / "blurry.eml", attachments=[{"filename": "IMG_2231.jpg"}])
    info = make_info(
        confidence=0.32,
        host_university="Invented University",
        start_date="1999-01-01",
        notes="blurry scan",
    )
    _patch_classifier(monkeypatch, env, info)
    report = env.pipeline.run_inbox(inbox, threshold=0.7)

    assert report["review"] == 1
    assert report["saved"] == 0
    row = read_students(env.xlsx)[0]
    assert row["HostUniversity"] is None
    assert row["StartDate"] is None
    assert row["Status"] == "needs_review"
    assert "confidence=0.32" in (env.review / "IMG_2231.jpg.reason.txt").read_text()


def test_missing_surname_forces_review(inbox, env, monkeypatch):
    make_email(inbox / "anon.eml", attachments=[{"filename": "scan.pdf"}])
    _patch_classifier(monkeypatch, env, make_info(student_surname="", confidence=0.99))
    report = env.pipeline.run_inbox(inbox)

    assert report["review"] == 1
    assert report["saved"] == 0


def test_high_confidence_is_saved_and_written_to_xlsx(inbox, env, monkeypatch):
    make_email(inbox / "good.eml", attachments=[{"filename": "scan_0042.pdf"}])
    _patch_classifier(monkeypatch, env, make_info())
    report = env.pipeline.run_inbox(inbox)

    assert report["saved"] == 1
    assert report["review"] == 0
    assert (env.out / "Garcia_Ana_LearningAgreement_2026-27.pdf").exists()
    row = read_students(env.xlsx)[0]
    assert row["Student"] == "Ana"
    assert row["HostUniversity"] == "University of Bologna"
    assert row["StartDate"] == "2026-09-01"
    assert row["Status"] == "ok"


def test_oversized_attachment_is_rejected_before_the_llm(inbox, env, monkeypatch):
    make_email(
        inbox / "huge.eml",
        attachments=[{"filename": "huge.pdf", "data": b"x" * 5000}],
    )
    monkeypatch.setattr(env.pipeline.llm, "MAX_ATTACHMENT_BYTES", 10)
    report = env.pipeline.run_inbox(inbox)

    assert report["review"] == 1
    assert report["saved"] == 0
    assert "too large" in report["results"][0]["errors"][0]


def test_two_attachments_same_target_get_unique_names(inbox, env, monkeypatch):
    make_email(
        inbox / "two.eml",
        attachments=[
            {"filename": "part1.pdf", "data": b"one"},
            {"filename": "part2.pdf", "data": b"two"},
        ],
    )
    _patch_classifier(monkeypatch, env, make_info())
    report = env.pipeline.run_inbox(inbox)

    assert sorted(report["results"][0]["saved"]) == [
        "Garcia_Ana_LearningAgreement_2026-27-2.pdf",
        "Garcia_Ana_LearningAgreement_2026-27.pdf",
    ]


def test_reprocessing_is_idempotent(inbox, env, monkeypatch):
    make_email(inbox / "good.eml", attachments=[{"filename": "scan.pdf"}])
    _patch_classifier(monkeypatch, env, make_info())
    env.pipeline.run_inbox(inbox)
    report = env.pipeline.run_inbox(inbox)

    rows = read_students(env.xlsx)
    assert len(rows) == 1
    assert report["saved"] == 1
    assert rows[0]["Documents"].count("LearningAgreement") == 1


def test_one_broken_email_does_not_stop_the_batch(inbox, env, monkeypatch):
    (inbox / "broken.eml").write_bytes(b"\x00\xff broken")
    make_email(inbox / "good.eml", attachments=[{"filename": "scan.pdf"}])
    _patch_classifier(monkeypatch, env, make_info())
    report = env.pipeline.run_inbox(inbox)

    assert report["emails"] == 2
    assert report["saved"] == 1
    assert report["skipped"] == 1
    assert report["errors"] == 0


def test_excel_merges_multiple_documents_for_one_student(inbox, env, monkeypatch):
    make_email(inbox / "la.eml", attachments=[{"filename": "la.pdf"}])
    _patch_classifier(monkeypatch, env, make_info())
    env.pipeline.run_inbox(inbox)

    make_email(inbox / "insurance.eml", attachments=[{"filename": "insurance.pdf"}])
    _patch_classifier(
        monkeypatch,
        env,
        make_info(doc_type=DocType.insurance, host_university="", start_date=""),
    )
    env.pipeline.run_inbox(inbox)

    rows = read_students(env.xlsx)
    assert len(rows) == 1
    assert "LearningAgreement" in rows[0]["Documents"]
    assert "Insurance" in rows[0]["Documents"]
    assert "Insurance" not in rows[0]["Missing"]
    assert rows[0]["HostUniversity"] == "University of Bologna"


def test_disk_error_is_reported_not_raised(inbox, env, monkeypatch):
    make_email(inbox / "good.eml", attachments=[{"filename": "scan.pdf"}])
    _patch_classifier(monkeypatch, env, make_info())

    def broken_save(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(env.pipeline, "save_document", broken_save)
    report = env.pipeline.run_inbox(inbox)

    assert report["saved"] == 0
    assert report["errors"] == 1
    assert "disk full" in report["results"][0]["errors"][0]


def test_threshold_zero_accepts_low_confidence(inbox, env, monkeypatch):
    make_email(inbox / "ok.eml", attachments=[{"filename": "scan.pdf"}])
    _patch_classifier(monkeypatch, env, make_info(confidence=0.2))
    report = env.pipeline.run_inbox(inbox, threshold=0.0)

    assert report["saved"] == 1
    assert report["review"] == 0


def test_document_info_defaults_are_safe():
    info = DocumentInfo()
    assert info.doc_type == DocType.other
    assert info.confidence == 0.0
    assert info.student_surname == ""
