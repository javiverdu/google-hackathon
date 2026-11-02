"""Model fallback and input guards, no network calls."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import erasmus_agent.llm as llm
from tests.helpers import make_info


class FakeModels:
    def __init__(self, fail_models, result=None):
        self.fail_models = set(fail_models)
        self.result = result or make_info()
        self.calls: list[str] = []

    def generate_content(self, model, contents, config=None):
        self.calls.append(model)
        if model in self.fail_models:
            raise RuntimeError(f"503 UNAVAILABLE for {model}")
        return SimpleNamespace(parsed=self.result, text="answer")


def _client_with(models):
    return SimpleNamespace(models=models)


def test_falls_back_when_primary_model_is_overloaded(monkeypatch):
    models = FakeModels(fail_models={llm.GEMINI_MODEL})
    monkeypatch.setattr(llm, "_client", lambda: _client_with(models))

    info = llm.classify_document({"subject": "s", "body": "b"}, {"name": "a.pdf", "data": b"%PDF"})

    assert info.student_surname == "Garcia"
    assert models.calls[0] == llm.GEMINI_MODEL
    assert models.calls[1] == llm.GEMINI_FALLBACK_MODELS[0]


def test_all_models_failing_raises_clear_error(monkeypatch):
    models = FakeModels(fail_models={llm.GEMINI_MODEL, *llm.GEMINI_FALLBACK_MODELS})
    monkeypatch.setattr(llm, "_client", lambda: _client_with(models))

    with pytest.raises(RuntimeError) as error:
        llm.classify_document({"subject": "s", "body": "b"}, {"name": "a.pdf", "data": b"%PDF"})

    assert "All Gemini models failed" in str(error.value)
    assert llm.GEMINI_MODEL in str(error.value)


def test_unsupported_type_never_calls_the_model(monkeypatch):
    models = FakeModels(fail_models=set())
    monkeypatch.setattr(llm, "_client", lambda: _client_with(models))

    with pytest.raises(ValueError, match="Unsupported attachment type"):
        llm.classify_document({}, {"name": "a.docx", "data": b"PK", "content_type": "application/msword"})

    assert models.calls == []


def test_empty_attachment_is_rejected(monkeypatch):
    models = FakeModels(fail_models=set())
    monkeypatch.setattr(llm, "_client", lambda: _client_with(models))

    with pytest.raises(ValueError, match="Empty attachment"):
        llm.classify_document({}, {"name": "a.pdf", "data": b""})

    assert models.calls == []


def test_oversized_attachment_is_rejected(monkeypatch):
    models = FakeModels(fail_models=set())
    monkeypatch.setattr(llm, "_client", lambda: _client_with(models))
    monkeypatch.setattr(llm, "MAX_ATTACHMENT_BYTES", 10)

    with pytest.raises(ValueError, match="too large"):
        llm.classify_document({}, {"name": "a.pdf", "data": b"%PDF" + b"x" * 100})

    assert models.calls == []


def test_answer_question_uses_fallback_and_returns_text(monkeypatch):
    models = FakeModels(fail_models={llm.GEMINI_MODEL})
    monkeypatch.setattr(llm, "_client", lambda: _client_with(models))

    answer = llm.answer_question("When is the deadline?", "## Deadline\n15 October 2026", "")
    assert answer == "answer"
    assert len(models.calls) == 2


def test_unknown_mime_is_guessed_from_filename(monkeypatch):
    models = FakeModels(fail_models=set())
    monkeypatch.setattr(llm, "_client", lambda: _client_with(models))

    llm.classify_document(
        {},
        {
            "name": "photo.jpg",
            "data": b"jpgbytes",
            "content_type": "application/octet-stream",
        },
    )
    assert models.calls


def test_fallback_list_has_no_duplicates():
    models = [llm.GEMINI_MODEL, *llm.GEMINI_FALLBACK_MODELS]
    assert len(models) == len(set(models))
