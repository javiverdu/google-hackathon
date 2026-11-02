"""Escalations are persisted so staff actually see them."""

from __future__ import annotations

from erasmus_agent.tools.escalation import HEADERS, log_escalation, read_escalations


def test_missing_file_returns_empty(tmp_path):
    assert read_escalations(tmp_path / "none.csv") == []


def test_escalation_writes_header_and_row(tmp_path):
    path = tmp_path / "escalations.csv"
    log_escalation("Can I bring my dog?", reason="not in FAQ", student="Maria Rossi", path=path)

    rows = read_escalations(path)
    assert len(rows) == 1
    assert list(rows[0]) == HEADERS
    assert rows[0]["student"] == "Maria Rossi"
    assert rows[0]["question"] == "Can I bring my dog?"
    assert rows[0]["reason"] == "not in FAQ"


def test_multiline_question_is_flattened(tmp_path):
    path = tmp_path / "escalations.csv"
    log_escalation("Line one\nLine two\twith tab", path=path)
    rows = read_escalations(path)
    assert rows[0]["question"] == "Line one Line two with tab"


def test_multiple_escalations_append(tmp_path):
    path = tmp_path / "escalations.csv"
    log_escalation("first", path=path)
    log_escalation("second", path=path)
    assert [row["question"] for row in read_escalations(path)] == ["first", "second"]


def test_escalation_parent_folder_is_created(tmp_path):
    path = tmp_path / "nested" / "deeper" / "escalations.csv"
    log_escalation("hello", path=path)
    assert path.exists()
