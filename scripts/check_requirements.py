"""Check the must-have requirements against the generated artifacts.

Usage:
    python scripts/check_requirements.py

Exit code 0 = all checks pass. No Gemini calls.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from erasmus_agent.schemas import parse_date  # noqa: E402
from erasmus_agent.tools.email_reader import iter_inbox  # noqa: E402
from erasmus_agent.tools.excel_writer import read_students  # noqa: E402
from erasmus_agent.tools.faq import load_faq, search_faq  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NAMING = re.compile(
    r"^[A-Za-z0-9]+_[A-Za-z0-9]+_"
    r"(LearningAgreement|Transcript|Insurance|CertificateOfArrival)_"
    r"\d{4}-\d{2}\.(pdf|jpg|jpeg|png)$"
)
REQUIRED_COLUMNS = {
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
}

checks: list[tuple[bool, str]] = []


def check(condition: bool, label: str, detail: str = "") -> None:
    checks.append((bool(condition), f"{label}{(': ' + detail) if detail else ''}"))


def main() -> int:
    inbox = ROOT / "data" / "inbox"
    out = ROOT / "data" / "out"
    review = ROOT / "data" / "review"
    xlsx = ROOT / "data" / "students.xlsx"
    faq = load_faq()

    emails = list(iter_inbox(inbox))
    attachments = sum(len(meta["attachments"]) for meta in emails)
    check(len(emails) >= 10, "sample inbox has at least 10 emails", str(len(emails)))
    check(attachments >= 8, "emails carry attachments", str(attachments))

    saved = (
        [path for path in out.iterdir() if path.is_file() and not path.name.startswith(".")]
        if out.exists()
        else []
    )
    check(len(saved) >= 8, "renamed documents in data/out", str(len(saved)))
    bad_names = [path.name for path in saved if not NAMING.match(path.name)]
    check(not bad_names, "all saved files follow Surname_Name_DocType_YYYY-YY.ext", ", ".join(bad_names))

    review_files = [
        path
        for path in review.iterdir()
        if path.is_file() and not path.name.startswith(".") and not path.name.endswith(".reason.txt")
    ] if review.exists() else []
    check(bool(review_files), "uncertain documents are sent to review", str(len(review_files)))
    reasons = list(review.glob("*.reason.txt")) if review.exists() else []
    check(bool(reasons), "review files carry a human-readable reason", str(len(reasons)))

    rows = read_students(xlsx)
    check(bool(rows), "students.xlsx exists with rows", str(len(rows)))
    if rows:
        check(REQUIRED_COLUMNS.issubset(rows[0].keys()), "spreadsheet has all required columns")
        keys = {(str(row["Student"]), str(row["Surname"])) for row in rows}
        check(len(keys) == len(rows), "one row per student", f"{len(rows)} rows / {len(keys)} students")
        accepted = [row for row in rows if row.get("Status") == "ok"]
        check(len(accepted) >= 7, "accepted students in the spreadsheet", str(len(accepted)))
        incomplete = [
            row["Student"]
            for row in accepted
            if not (row.get("StartDate") and row.get("EndDate") and row.get("Deadline"))
        ]
        check(not incomplete, "every accepted student has stay dates and deadline", ", ".join(incomplete))
        invalid_dates = [
            (row["Student"], value)
            for row in rows
            for value in (row.get("StartDate"), row.get("EndDate"), row.get("Deadline"))
            if value and parse_date(str(value)) is None
        ]
        check(not invalid_dates, "all dates parse as ISO", str(invalid_dates[:3]))
        missing = [row for row in rows if row.get("Missing")]
        check(len(missing) >= 1, "missing documents are flagged", str(len(missing)))

    known = search_faq("When is the deadline to submit the Learning Agreement?", faq)
    check(bool(known), "FAQ answers known questions")
    unknown = search_faq("Can I bring my dog to the university?", faq)
    check(unknown == "", "FAQ leaves unknown questions for a person")

    print("Erasmus DocFlow — requirement checks\n")
    failures = 0
    for ok, label in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
        failures += 0 if ok else 1
    print(f"\n{len(checks) - failures}/{len(checks)} checks passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
