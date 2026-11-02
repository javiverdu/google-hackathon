"""Shared fixtures: temp inbox and isolated pipeline outputs."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import erasmus_agent.pipeline as pipeline


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
    return SimpleNamespace(out=out, review=review, xlsx=xlsx, pipeline=pipeline)
