"""Save attachments under the shared naming pattern."""

from __future__ import annotations

import json
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


def _sidecar_path(target: Path) -> Path:
    return target.with_suffix(target.suffix + ".json")


def move_to_review(
    data: bytes,
    original_name: str,
    review_dir: str | Path,
    reason: str = "",
    info: DocumentInfo | None = None,
    source_email: str = "",
) -> Path:
    """Store uncertain documents for a human, keeping a cleaned original name.

    Writes a .json sidecar with the reason and whatever the model guessed
    (even if wrong), so the review UI can pre-fill a correction form.
    """
    target_dir = Path(review_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = _sanitize_stem(Path(original_name).stem)
    suffix = _sanitize_stem(file_suffix(original_name).lstrip("."), "bin", max_length=10)
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    target = target_dir / f"{stem}{suffix}"
    counter = 2
    while target.exists():
        try:
            same = target.read_bytes() == data
        except OSError:
            same = False
        if same:
            if reason:
                target.with_suffix(target.suffix + ".reason.txt").write_text(reason, encoding="utf-8")
            return target  # reprocessing the same email: keep one review copy
        target = target_dir / f"{stem}-{counter}{suffix}"
        counter += 1
    target.write_bytes(data)
    _sidecar_path(target).write_text(
        json.dumps(
            {
                "reason": reason,
                "source_email": source_email,
                "original_name": original_name,
                "extracted": info.model_dump(mode="json") if info else {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if reason:
        target.with_suffix(target.suffix + ".reason.txt").write_text(reason, encoding="utf-8")
    return target


def read_review_sidecar(path: str | Path) -> dict:
    """Read the .json sidecar for a review-folder document, if any."""
    sidecar = _sidecar_path(Path(path))
    if not sidecar.exists():
        return {}
    return json.loads(sidecar.read_text(encoding="utf-8"))


def list_review_items(review_dir: str | Path) -> list[Path]:
    """Every document currently waiting for a human in the review folder."""
    folder = Path(review_dir)
    if not folder.is_dir():
        return []
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file()
        and path.suffix != ".json"
        and not path.name.endswith(".reason.txt")
        and path.name != ".gitkeep"
    )


def discard_review_item(path: str | Path) -> None:
    """Remove a review document and its sidecars without saving it anywhere."""
    path = Path(path)
    _sidecar_path(path).unlink(missing_ok=True)
    path.with_suffix(path.suffix + ".reason.txt").unlink(missing_ok=True)
    path.unlink(missing_ok=True)


def approve_review_item(
    path: str | Path,
    info: DocumentInfo,
    out_dir: str | Path,
) -> Path:
    """Human confirmed/corrected the fields: save properly and clear the review entry."""
    path = Path(path)
    target = save_document(path.read_bytes(), path.name, info, out_dir)
    discard_review_item(path)
    return target
