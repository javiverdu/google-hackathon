"""Save attachments under the shared naming pattern."""

from __future__ import annotations

from pathlib import Path

from ..schemas import DocumentInfo, build_filename, file_suffix


def save_document(
    data: bytes,
    original_name: str,
    info: DocumentInfo,
    out_dir: str | Path,
) -> Path:
    """Write bytes to out_dir/Surname_Name_DocType_2026-27.ext, never overwrite."""
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    name = build_filename(info, file_suffix(original_name))
    target = target_dir / name
    counter = 2
    while target.exists():
        target = target_dir / f"{Path(name).stem}-{counter}{Path(name).suffix}"
        counter += 1
    target.write_bytes(data)
    return target


def move_to_review(
    data: bytes,
    original_name: str,
    review_dir: str | Path,
    reason: str = "",
) -> Path:
    """Store uncertain documents for a human, keeping the original name."""
    target_dir = Path(review_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(original_name).stem or "document"
    suffix = file_suffix(original_name)
    target = target_dir / f"{stem}{suffix}"
    counter = 2
    while target.exists():
        target = target_dir / f"{stem}-{counter}{suffix}"
        counter += 1
    target.write_bytes(data)
    if reason:
        target.with_suffix(target.suffix + ".reason.txt").write_text(reason, encoding="utf-8")
    return target
