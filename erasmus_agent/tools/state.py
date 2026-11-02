"""Export, restore and reset the demo data.

Streamlit Community Cloud wipes the container on sleep or reboot, so the app
can save everything generated at runtime into one `.zip` and restore it later.
The inbox is never exported or deleted: the sample emails live in the repo.
"""

from __future__ import annotations

import io
import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from .. import config

BUNDLE_FILES = ("students.xlsx", "escalations.csv")
BUNDLE_DIRS = ("out", "review")
MAX_BUNDLE_BYTES = 200 * 1024 * 1024


def _data_dir(data_dir: str | Path | None) -> Path:
    return Path(data_dir) if data_dir else config.DATA_DIR


def _count(folder: Path, skip: tuple[str, ...] = ()) -> int:
    if not folder.is_dir():
        return 0
    return sum(
        1
        for path in folder.iterdir()
        if path.is_file()
        and not path.name.startswith(".")
        and not any(path.name.endswith(suffix) for suffix in skip)
    )


def state_summary(data_dir: str | Path | None = None) -> dict:
    """Counts shown in the UI before exporting or resetting."""
    root = _data_dir(data_dir)
    return {
        "documents": _count(root / "out"),
        "review": _count(root / "review", skip=(".reason.txt",)),
        "spreadsheet": (root / "students.xlsx").exists(),
        "escalations": (root / "escalations.csv").exists(),
    }


def export_state(data_dir: str | Path | None = None) -> bytes:
    """Bundle the generated spreadsheet, documents, review files and escalations."""
    root = _data_dir(data_dir)
    files: list[Path] = []

    for name in BUNDLE_FILES:
        path = root / name
        if path.is_file():
            files.append(path)
    for folder_name in BUNDLE_DIRS:
        folder = root / folder_name
        if folder.is_dir():
            files.extend(
                path
                for path in sorted(folder.iterdir())
                if path.is_file() and not path.name.startswith(".")
            )

    manifest = {
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "files": len(files),
        "summary": state_summary(root),
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            bundle.write(path, arcname=path.relative_to(root).as_posix())
        bundle.writestr("manifest.json", json.dumps(manifest, indent=2))
    return buffer.getvalue()


def _safe_member(name: str) -> bool:
    parts = PurePosixPath(name).parts
    if not parts or name.startswith("/") or "\\" in name:
        return False
    if any(part in {"..", "."} for part in parts):
        return False
    if len(parts) == 1:
        return parts[0] in BUNDLE_FILES
    return len(parts) == 2 and parts[0] in BUNDLE_DIRS


def restore_state(data: bytes, data_dir: str | Path | None = None) -> dict:
    """Replace generated files with the bundle contents. The inbox is untouched."""
    root = _data_dir(data_dir)
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError("Bundle too large (max 200 MB).")

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            members = [info for info in bundle.infolist() if not info.is_dir()]
            if not members:
                raise ValueError("Bundle is empty.")
            if sum(info.file_size for info in members) > MAX_BUNDLE_BYTES:
                raise ValueError("Bundle expands to more than 200 MB.")
            for info in members:
                if info.filename != "manifest.json" and not _safe_member(info.filename):
                    raise ValueError(f"Unexpected file in bundle: {info.filename}")

            for folder_name in BUNDLE_DIRS:
                folder = root / folder_name
                if folder.exists():
                    shutil.rmtree(folder)
                folder.mkdir(parents=True, exist_ok=True)

            restored = 0
            for info in members:
                if info.filename == "manifest.json":
                    continue
                target = root / PurePosixPath(info.filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bundle.read(info))
                restored += 1
    except zipfile.BadZipFile as exc:
        raise ValueError("That file is not a valid .zip bundle.") from exc

    return {"files": restored, "summary": state_summary(root)}


def reset_demo_data(data_dir: str | Path | None = None) -> dict:
    """Delete generated files. Keeps the inbox and dotfiles such as .gitkeep."""
    root = _data_dir(data_dir)
    removed = 0
    for folder_name in BUNDLE_DIRS:
        folder = root / folder_name
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.name.startswith("."):
                continue
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed += 1
    for name in BUNDLE_FILES:
        path = root / name
        if path.is_file():
            path.unlink()
            removed += 1
    return {"removed": removed, "summary": state_summary(root)}
