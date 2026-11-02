"""One row per student in students.xlsx, updated idempotently."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook

from ..schemas import REQUIRED_DOCS, DocType, DocumentInfo

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
]


def _key(first: str, surname: str) -> str:
    return f"{first.strip().lower()}|{surname.strip().lower()}"


def _open(path: Path):
    if path.exists():
        workbook = load_workbook(path)
        sheet = workbook.active
        if sheet.max_row == 1 and sheet["A1"].value is None:
            sheet.append(HEADERS)
    else:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Students"
        sheet.append(HEADERS)
    return workbook, sheet


def upsert_student(
    path: str | Path,
    info: DocumentInfo,
    saved_filename: str = "",
    status: str = "ok",
) -> Path:
    """Insert or merge one document into the student's row."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook, sheet = _open(path)

    row_index = None
    for row in range(2, sheet.max_row + 1):
        if _key(str(sheet.cell(row, 1).value or ""), str(sheet.cell(row, 2).value or "")) == _key(
            info.student_first_name, info.student_surname
        ):
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

    present = set()
    for name in str(sheet.cell(row_index, 8).value or "").split(", "):
        for doc in DocType:
            if doc.value in name:
                present.add(doc)
    missing = [doc.value for doc in REQUIRED_DOCS if doc not in present]
    sheet.cell(row_index, 9, ", ".join(missing) or "-")
    sheet.cell(row_index, 10, status)

    workbook.save(path)
    return path


def read_students(path: str | Path) -> list[dict]:
    """Used by the Streamlit dashboard."""
    path = Path(path)
    if not path.exists():
        return []
    sheet = load_workbook(path).active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(cell or "") for cell in rows[0]]
    return [dict(zip(headers, row)) for row in rows[1:] if any(row)]
