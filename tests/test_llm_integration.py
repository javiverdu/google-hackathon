"""Optional real-Gemini checks. Run before the demo:

    RUN_LLM_TESTS=1 pytest tests/test_llm_integration.py -v

Skipped by default so CI and teammates without a key stay green.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from erasmus_agent import llm
from erasmus_agent.schemas import DocType
from erasmus_agent.tools.email_reader import read_email
from erasmus_agent.tools.excel_writer import read_students
from erasmus_agent.tools.faq import load_faq

pytestmark = pytest.mark.integration

INBOX = Path(__file__).resolve().parent.parent / "data" / "inbox"

if os.getenv("RUN_LLM_TESTS") != "1":
    pytest.skip("set RUN_LLM_TESTS=1 to call Gemini", allow_module_level=True)


@pytest.mark.skipif(not (INBOX / "email_01.eml").exists(), reason="sample data missing")
def test_real_learning_agreement_classification():
    meta = read_email(INBOX / "email_01.eml")
    info = llm.classify_document(meta, meta["attachments"][0])

    assert info.doc_type == DocType.learning_agreement
    assert info.student_surname.lower() == "garcia lopez"
    assert info.student_first_name.lower() == "ana"
    assert info.semester == "2026-27"
    assert info.start_date == "2026-09-01"
    assert info.confidence >= 0.7


@pytest.mark.skipif(not (INBOX / "email_07.eml").exists(), reason="sample data missing")
def test_real_blurry_scan_is_flagged_low_confidence():
    meta = read_email(INBOX / "email_07.eml")
    info = llm.classify_document(meta, meta["attachments"][0])
    assert info.confidence < 0.7


def test_real_faq_answers_and_escalates():
    faq = load_faq()
    answer = llm.answer_question(
        "When is the deadline to submit the Learning Agreement?", faq, ""
    )
    assert "15 October 2026" in answer or "15 October" in answer

    escalation = llm.answer_question("Can I bring my dog to the host university?", faq, "")
    assert escalation.startswith("ESCALATE")


def test_real_faq_uses_student_status():
    rows = read_students(Path(__file__).resolve().parent.parent / "data" / "students.xlsx")
    if not rows:
        pytest.skip("run the app once to create students.xlsx")
    context = "\n".join(str(row) for row in rows)
    answer = llm.answer_question(
        "Did you get my insurance? I am Maria Rossi", load_faq(), context
    )
    assert "insurance" in answer.lower()
