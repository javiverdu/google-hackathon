"""Save attachments under the shared naming pattern."""

from __future__ import annotations

import re
from pathlib import Path

from ..schemas import DocumentInfo, build_filename, file_suffix

MAX_NAME_LENGTH = 120
_UNSAFE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _sanitize_stem(value: str, fallback: str = "document", max_length: int = 80) -> str:
    """Keep unicode letters but remove path separators and Windows-reserved chars."""
    cleaned = _UNSAFE.sub("_", value or "").strip(" ._")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:max_length] or fallback


def _fit_length(name: str, max_length: int = MAX_NAME_LENGTH) -> str:
    if len(name) <= max_length:
        return name
    path = Path(name)
    stem = path.stem[: max_length - len(path.suffix)]
    return f"{stem}{path.suffix}"


def save_document(
    data: bytes,
    original_name: str,
    info: DocumentInfo,
    out_dir: str | Path,
) -> Path:
    """Write bytes to out_dir/Surname_Name_DocType_2026-27.ext, never overwrite."""
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    name = _fit_length(build_filename(info, file_suffix(original_name)))
    target = target_dir / name
    if target.exists() and target.read_bytes() == data:
        return target  # reprocessing the same email: keep one file
    counter = 2
    while target.exists():
        stem = Path(name).stem[: MAX_NAME_LENGTH - len(Path(name).suffix) - 4]
        target = target_dir / f"{stem}-{counter}{Path(name).suffix}"
        counter += 1
    target.write_bytes(data)
    return target


def move_to_review(
    data: bytes,
    original_name: str,
    review_dir: str | Path,
    reason: str = "",
) -> Path:
    """Store uncertain documents for a human, keeping a cleaned original name."""
    target_dir = Path(review_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = _sanitize_stem(Path(original_name).stem)
    suffix = _sanitize_stem(file_suffix(original_name).lstrip("."), "bin", max_length=10)
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    target = target_dir / f"{stem}{suffix}"
    counter = 2
    while target.exists():
        target = target_dir / f"{stem}-{counter}{suffix}"
        counter += 1
    target.write_bytes(data)
    if reason:
        target.with_suffix(target.suffix + ".reason.txt").write_text(reason, encoding="utf-8")
    return target
