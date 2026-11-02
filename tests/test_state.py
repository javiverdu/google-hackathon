"""Demo state bundle: export, restore and reset without touching the inbox."""

from __future__ import annotations

import io
import zipfile

import pytest

from erasmus_agent.tools.state import (
    export_state,
    reset_demo_data,
    restore_state,
    state_summary,
)


def make_data_dir(tmp_path):
    root = tmp_path / "data"
    (root / "out").mkdir(parents=True)
    (root / "review").mkdir(parents=True)
    (root / "inbox").mkdir(parents=True)
    (root / "out" / "Garcia_Ana_LearningAgreement_2026-27.pdf").write_bytes(b"%PDF-1.4 out")
    (root / "out" / ".gitkeep").write_text("")
    (root / "review" / "foto_borrosa.jpg").write_bytes(b"\xff\xd8\xff review")
    (root / "review" / "foto_borrosa.jpg.reason.txt").write_text("confidence=0.31")
    (root / "students.xlsx").write_bytes(b"fake xlsx")
    (root / "escalations.csv").write_text("timestamp,question\n2026-11-02,Can I bring my dog?\n")
    (root / "inbox" / "email_01.eml").write_text("Subject: Hello\n\nbody")
    return root


def test_summary_counts_generated_files(tmp_path):
    root = make_data_dir(tmp_path)
    summary = state_summary(root)
    assert summary == {
        "documents": 1,
        "review": 1,
        "spreadsheet": True,
        "escalations": True,
    }


def test_export_contains_generated_files_only(tmp_path):
    root = make_data_dir(tmp_path)
    with zipfile.ZipFile(io.BytesIO(export_state(root))) as bundle:
        names = set(bundle.namelist())

    assert "students.xlsx" in names
    assert "escalations.csv" in names
    assert "out/Garcia_Ana_LearningAgreement_2026-27.pdf" in names
    assert "review/foto_borrosa.jpg.reason.txt" in names
    assert "manifest.json" in names
    assert not any(name.startswith("inbox/") for name in names)
    assert "out/.gitkeep" not in names


def test_export_of_empty_state_is_a_valid_bundle(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    with zipfile.ZipFile(io.BytesIO(export_state(root))) as bundle:
        assert bundle.namelist() == ["manifest.json"]


def test_roundtrip_restores_everything_and_keeps_inbox(tmp_path):
    root = make_data_dir(tmp_path)
    bundle = export_state(root)

    for name in ("students.xlsx", "escalations.csv"):
        (root / name).unlink()
    (root / "out" / "Garcia_Ana_LearningAgreement_2026-27.pdf").unlink()

    result = restore_state(bundle, root)

    assert result["files"] == 5
    assert (root / "out" / "Garcia_Ana_LearningAgreement_2026-27.pdf").read_bytes() == b"%PDF-1.4 out"
    assert (root / "review" / "foto_borrosa.jpg.reason.txt").read_text() == "confidence=0.31"
    assert (root / "students.xlsx").read_bytes() == b"fake xlsx"
    assert (root / "escalations.csv").exists()
    assert (root / "inbox" / "email_01.eml").exists()


def test_restore_replaces_stale_generated_files(tmp_path):
    root = make_data_dir(tmp_path)
    bundle = export_state(root)
    (root / "out" / "Old_Doc_Other_2025-26.pdf").write_bytes(b"stale")

    restore_state(bundle, root)

    assert not (root / "out" / "Old_Doc_Other_2025-26.pdf").exists()


def test_restore_rejects_path_traversal(tmp_path):
    root = make_data_dir(tmp_path)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr("out/../../../etc/passwd", "boom")

    with pytest.raises(ValueError, match="Unexpected file"):
        restore_state(buffer.getvalue(), root)
    assert not (tmp_path / "etc").exists()


def test_restore_rejects_unexpected_member(tmp_path):
    root = make_data_dir(tmp_path)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr("run.sh", "rm -rf /")

    with pytest.raises(ValueError, match="Unexpected file"):
        restore_state(buffer.getvalue(), root)


def test_restore_rejects_inbox_member(tmp_path):
    root = make_data_dir(tmp_path)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr("inbox/evil.eml", "Subject: x")

    with pytest.raises(ValueError, match="Unexpected file"):
        restore_state(buffer.getvalue(), root)


def test_restore_rejects_non_zip(tmp_path):
    root = make_data_dir(tmp_path)
    with pytest.raises(ValueError, match="not a valid .zip"):
        restore_state(b"this is not a zip", root)


def test_reset_keeps_inbox_and_dotfiles(tmp_path):
    root = make_data_dir(tmp_path)

    result = reset_demo_data(root)

    assert result["removed"] == 5
    assert list((root / "out").iterdir()) == [root / "out" / ".gitkeep"]
    assert list((root / "review").iterdir()) == []
    assert not (root / "students.xlsx").exists()
    assert not (root / "escalations.csv").exists()
    assert (root / "inbox" / "email_01.eml").exists()
    assert result["summary"]["documents"] == 0
