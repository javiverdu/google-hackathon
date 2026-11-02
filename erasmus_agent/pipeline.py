"""End-to-end inbox pipeline: email -> classification -> files -> spreadsheet."""

from __future__ import annotations

from pathlib import Path

from . import llm
from .config import CONFIDENCE_THRESHOLD, INBOX_DIR, OUT_DIR, REVIEW_DIR, SPREADSHEET
from .schemas import DocType, DocumentInfo
from .tools.email_reader import iter_inbox
from .tools.excel_writer import upsert_student
from .tools.file_saver import move_to_review, save_document


def _fallback_info(attachment_name: str) -> DocumentInfo:
    return DocumentInfo(
        doc_type=DocType.other,
        confidence=0.0,
        notes=f"Could not classify {attachment_name}",
    )


def _process_attachment(meta: dict, attachment: dict, threshold: float, result: dict) -> None:
    name = attachment.get("name", "document")
    try:
        info = llm.classify_document(meta, attachment)
    except Exception as exc:
        info = _fallback_info(name)
        result["errors"].append(f"{name}: {exc}")

    uncertain = (
        info.confidence < threshold
        or info.doc_type == DocType.other
        or not info.student_surname
    )
    if uncertain:
        target = move_to_review(
            attachment["data"],
            name,
            REVIEW_DIR,
            reason=f"confidence={info.confidence:.2f} type={info.doc_type.value} notes={info.notes}",
        )
        result["review"].append(target.name)
        # Keep the row honest: no guessed dates or university from a low-confidence scan.
        review_info = DocumentInfo(
            student_first_name=info.student_first_name,
            student_surname=info.student_surname,
            doc_type=info.doc_type,
            semester=info.semester,
            confidence=info.confidence,
            notes=info.notes,
        )
        upsert_student(SPREADSHEET, review_info, status="needs_review")
        return

    target = save_document(attachment["data"], name, info, OUT_DIR)
    result["saved"].append(target.name)
    upsert_student(SPREADSHEET, info, saved_filename=target.name, status="ok")


def process_email(meta: dict, threshold: float = CONFIDENCE_THRESHOLD) -> dict:
    """Process every attachment of one email. Returns a report entry."""
    result = {
        "email": meta.get("filename", ""),
        "subject": meta.get("subject", ""),
        "sender": meta.get("sender", ""),
        "saved": [],
        "review": [],
        "errors": [meta["error"]] if meta.get("error") else [],
        "skipped": [],
    }

    if not meta.get("attachments"):
        result["skipped"].append("No attachments (question only)")
        return result

    for attachment in meta["attachments"]:
        try:
            _process_attachment(meta, attachment, threshold, result)
        except Exception as exc:  # disk errors, corrupt payloads, Excel locked...
            result["errors"].append(f"{attachment.get('name', 'document')}: {exc}")

    return result


def _error_entry(meta: dict, exc: Exception) -> dict:
    return {
        "email": meta.get("filename", ""),
        "subject": meta.get("subject", ""),
        "sender": meta.get("sender", ""),
        "saved": [],
        "review": [],
        "errors": [str(exc)],
        "skipped": [],
    }


def run_inbox(
    inbox_dir: str | Path = INBOX_DIR,
    threshold: float = CONFIDENCE_THRESHOLD,
    limit: int | None = None,
) -> dict:
    """Run the whole inbox. This is what the UI button calls."""
    emails = list(iter_inbox(inbox_dir))
    if limit:
        emails = emails[:limit]

    results: list[dict] = []
    for meta in emails:
        try:
            results.append(process_email(meta, threshold))
        except Exception as exc:  # one bad email never stops the batch
            results.append(_error_entry(meta, exc))

    return {
        "emails": len(results),
        "saved": sum(len(item["saved"]) for item in results),
        "review": sum(len(item["review"]) for item in results),
        "errors": sum(len(item["errors"]) for item in results),
        "skipped": sum(len(item["skipped"]) for item in results),
        "results": results,
    }
