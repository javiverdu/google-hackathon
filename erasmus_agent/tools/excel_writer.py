"""One row per student in students.xlsx, plus a Documents detail sheet."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook

from ..schemas import REQUIRED_DOCS, DocType, DocumentInfo, is_expired

HEADERS = [
    "Student",
    "Surname",
    "Semester",
    "HostUniversity",
    "StartDate",
    "EndDate",
    "Deadline",
    "Documents",
    "Missing",
    "Status",
    "Expired",
]

DOC_HEADERS = [
    "Student",
    "Surname",
    "DocType",
    "Filename",
    "Semester",
    "HostUniversity",
    "StartDate",
    "EndDate",
    "Deadline",
]


def _key(first: str, surname: str) -> str:
    return f"{first.strip().lower()}|{surname.strip().lower()}"


def _ensure_headers(sheet, headers: list[str]) -> None:
    existing = [str(cell.value) for cell in sheet[1] if cell.value]
    if not existing:
        for column, header in enumerate(headers, start=1):
            sheet.cell(1, column, header)
        return
    for header in headers:
        if header not in existing:
            sheet.cell(1, len(existing) + 1, header)
            existing.append(header)


def _open(path: Path):
    if path.exists():
        workbook = load_workbook(path)
        students = workbook.active
        students.title = "Students"
    else:
        workbook = Workbook()
        students = workbook.active
        students.title = "Students"

    _ensure_headers(students, HEADERS)
    if "Documents" in workbook.sheetnames:
        documents = workbook["Documents"]
    else:
        documents = workbook.create_sheet("Documents")
    _ensure_headers(documents, DOC_HEADERS)
    return workbook, students, documents


def _expired_docs(documents, key: str, today: date | None = None) -> list[str]:
    expired: set[str] = set()
    for row in documents.iter_rows(min_row=2, values_only=True):
        if not row or len(row) < 8:
            continue
        student, surname, doc_type, _filename, _sem, _host, _start, end_date = row[:8]
        if _key(str(student or ""), str(surname or "")) != key:
            continue
        if is_expired(str(end_date or ""), today):
            expired.add(str(doc_type or "Other"))
    return sorted(expired)


def upsert_student(
    path: str | Path,
    info: DocumentInfo,
    saved_filename: str = "",
    status: str = "ok",
    today: date | None = None,
) -> Path:
    """Insert or merge one document into the student's row."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook, sheet, documents = _open(path)
    key = _key(info.student_first_name, info.student_surname)

    row_index = None
    for row in range(2, sheet.max_row + 1):
        if _key(str(sheet.cell(row, 1).value or ""), str(sheet.cell(row, 2).value or "")) == key:
            row_index = row
            break

    if row_index is None:
        sheet.append(
            [
                info.student_first_name,
                info.student_surname,
                info.semester,
                info.host_university,
                info.start_date,
                info.end_date,
                info.deadline,
                "",
                "",
                "",
                "",
            ]
        )
        row_index = sheet.max_row

    updates = {
        3: info.semester,
        4: info.host_university,
        5: info.start_date,
        6: info.end_date,
        7: info.deadline,
    }
    for column, value in updates.items():
        if value and not sheet.cell(row_index, column).value:
            sheet.cell(row_index, column, value)

    if saved_filename:
        current = str(sheet.cell(row_index, 8).value or "")
        names = [name for name in current.split(", ") if name]
        if saved_filename not in names:
            names.append(saved_filename)
            sheet.cell(row_index, 8, ", ".join(names))

        detail_index = None
        for row in range(2, documents.max_row + 1):
            if (
                _key(str(documents.cell(row, 1).value or ""), str(documents.cell(row, 2).value or ""))
                == key
                and str(documents.cell(row, 4).value or "") == saved_filename
            ):
                detail_index = row
                break
        values = [
            info.student_first_name,
            info.student_surname,
            info.doc_type.value,
            saved_filename,
            info.semester,
            info.host_university,
            info.start_date,
            info.end_date,
            info.deadline,
        ]
        if detail_index is None:
            documents.append(values)
        else:
            for column, value in enumerate(values, start=1):
                if value:
                    documents.cell(detail_index, column, value)

    present = set()
    for name in str(sheet.cell(row_index, 8).value or "").split(", "):
        for doc in DocType:
            if doc.value in name:
                present.add(doc)
    missing = [doc.value for doc in REQUIRED_DOCS if doc not in present]
    sheet.cell(row_index, 9, ", ".join(missing) or "-")

    expired = _expired_docs(documents, key, today)
    sheet.cell(row_index, 11, ", ".join(expired) or "-")
    current_status = str(sheet.cell(row_index, 10).value or "")
    if current_status == "needs_review" and status != "needs_review":
        status = "needs_review"  # never hide a review item behind a later good document
    sheet.cell(row_index, 10, status)

    workbook.save(path)
    return path


def read_students(path: str | Path) -> list[dict]:
    """Used by the Streamlit dashboard."""
    path = Path(path)
    if not path.exists():
        return []
    sheet = load_workbook(path)["Students"]
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(cell or "") for cell in rows[0]]
    return [dict(zip(headers, row)) for row in rows[1:] if any(row)]


def read_documents(path: str | Path) -> list[dict]:
    """Detail sheet: one row per stored document."""
    path = Path(path)
    if not path.exists():
        return []
    workbook = load_workbook(path)
    if "Documents" not in workbook.sheetnames:
        return []
    rows = list(workbook["Documents"].iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(cell or "") for cell in rows[0]]
    return [dict(zip(headers, row)) for row in rows[1:] if any(row)]
