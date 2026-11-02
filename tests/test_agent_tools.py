"""ADK tool functions: check agent-facing responses without calling Gemini."""

from __future__ import annotations

from erasmus_agent.agent import faq, list_inbox, naming_pattern, process_one, students


def test_list_inbox_finds_samples():
    assert len(list_inbox()) >= 10


def test_naming_pattern_for_known_type():
    assert naming_pattern("Ana", "García López", "LearningAgreement", "2026/2027") == (
        "GarciaLopez_Ana_LearningAgreement_2026-27.pdf"
    )


def test_naming_pattern_unknown_type_falls_back_to_other():
    assert naming_pattern("Ana", "Garcia", "Passport", "2026-27").endswith(
        "Garcia_Ana_Other_2026-27.pdf"
    )


def test_faq_tool_returns_relevant_block():
    answer = faq("When is the Learning Agreement deadline?")
    assert "deadline" in answer.lower() or "15 October" in answer


def test_faq_tool_unknown_question_returns_full_faq():
    answer = faq("Can I bring my dog to the host university?")
    assert answer  # full FAQ fallback for the LLM to decide / escalate


def test_students_tool_returns_rows_or_empty():
    rows = students()
    assert isinstance(rows, list)
    if rows:
        assert "Student" in rows[0]


def test_process_one_missing_email_returns_error():
    assert "not found" in process_one("does_not_exist.eml")["error"]
