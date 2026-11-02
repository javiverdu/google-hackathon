"""Shared fixtures: temp inbox and isolated pipeline outputs."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import erasmus_agent.pipeline as pipeline
import erasmus_agent.tools.status_log as status_log


@pytest.fixture
def inbox(tmp_path):
    folder = tmp_path / "inbox"
    folder.mkdir()
    return folder


@pytest.fixture
def env(tmp_path, monkeypatch):
    out = tmp_path / "out"
    review = tmp_path / "review"
    xlsx = tmp_path / "students.xlsx"
    monkeypatch.setattr(pipeline, "OUT_DIR", out)
    monkeypatch.setattr(pipeline, "REVIEW_DIR", review)
    monkeypatch.setattr(pipeline, "SPREADSHEET", xlsx)
    monkeypatch.setattr(status_log, "LOG_PATH", tmp_path / "processing_log.json")
    return SimpleNamespace(out=out, review=review, xlsx=xlsx, pipeline=pipeline)
