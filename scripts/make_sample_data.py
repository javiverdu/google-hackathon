"""Generate fake Erasmus emails with PDF/JPG attachments.

Usage:
    pip install -r requirements-dev.txt
    python scripts/make_sample_data.py

Writes into data/inbox/ (overwrites files with the same names) and creates
data/expected.csv with the ground truth for quick accuracy checks (for the
"clean" documents only -- the deliberately broken ones are left out since
there is no single right answer for them).
"""

from __future__ import annotations

import csv
import io
import random
from email.message import EmailMessage
from pathlib import Path

from fpdf import FPDF, XPos, YPos
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "data" / "inbox"

TEXT = "Helvetica"
NAVY = (31, 60, 136)
LIGHT_GREY = (235, 238, 244)


def make_pdf(lines: list[str], title: str = "ERASMUS+ PROGRAMME") -> bytes:
    """A document that looks like a real university form: letterhead band,
    title, then a bordered label/value table instead of a wall of text."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, pdf.w, 22, style="F")
    pdf.set_xy(10, 6)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(TEXT, "B", 14)
    pdf.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(10, 30)
    label_w, value_w, row_h = 50, pdf.epw - 50, 9
    fill = False
    for line in lines:
        if ":" in line:
            label, value = line.split(":", 1)
        else:
            label, value = "", line
        pdf.set_font(TEXT, "B", 10)
        pdf.set_fill_color(*LIGHT_GREY)
        pdf.cell(label_w, row_h, label.strip(), border=1, fill=fill)
        pdf.set_font(TEXT, "", 10)
        pdf.set_fill_color(255, 255, 255)
        pdf.cell(value_w, row_h, value.strip(), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        fill = not fill

    pdf.ln(10)
    pdf.set_font(TEXT, "I", 9)
    pdf.multi_cell(pdf.epw, 6, "This is a sample document generated for demo purposes only.")
    return bytes(pdf.output())


def make_image(lines: list[str], blur: bool = False, official: bool = True) -> bytes:
    image = Image.new("RGB", (900, 1200), "white")
    draw = ImageDraw.Draw(image)
    if official:
        draw.rectangle([(0, 0), (900, 90)], fill=(31, 60, 136))
        draw.text((30, 30), "ERASMUS+ PROGRAMME (scanned copy)", fill="white")
    y = 130 if official else 70
    for line in lines:
        draw.text((60, y), line, fill="black")
        y += 34
    if blur:
        image = image.filter(ImageFilter.GaussianBlur(radius=4))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=60)
    return buffer.getvalue()


def document(
    doc_type: str,
    student: str,
    host: str,
    start: str,
    end: str,
    deadline: str = "2026-10-15",
) -> list[str]:
    return [
        f"Document: {doc_type}",
        f"Student: {student}",
        f"Host university: {host}",
        f"Stay start: {start}",
        f"Stay end: {end}",
        f"Deadline: {deadline}",
        "Academic year: 2026-27",
        "Signed and stamped by the host university.",
    ]


def _letterhead(pdf: FPDF, title: str, doc_id: str, academic_year: str = "2026/2027") -> None:
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, pdf.w, 24, style="F")
    pdf.set_xy(10, 5)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(TEXT, "B", 14)
    pdf.cell(0, 8, "ERASMUS+ PROGRAMME", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font(TEXT, "", 10)
    pdf.cell(0, 6, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(10, 28)
    pdf.set_font(TEXT, "", 9)
    pdf.cell(0, 5, f"Document ID: {doc_id}    Academic year: {academic_year}")
    pdf.ln(12)


def _section(pdf: FPDF, label: str) -> None:
    pdf.set_font(TEXT, "B", 11)
    pdf.set_fill_color(*LIGHT_GREY)
    pdf.cell(0, 8, f"  {label}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)


def _kv_table(pdf: FPDF, rows: list[tuple[str, str]]) -> None:
    label_w, value_w, row_h = 55, pdf.epw - 55, 8
    fill = False
    for label, value in rows:
        pdf.set_font(TEXT, "B", 9.5)
        pdf.set_fill_color(*LIGHT_GREY if fill else (255, 255, 255))
        pdf.cell(label_w, row_h, f" {label}", border=1, fill=True)
        pdf.set_font(TEXT, "", 9.5)
        pdf.cell(value_w, row_h, f" {value}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        fill = not fill
    pdf.ln(4)


def _signature_block(pdf: FPDF, lines: list[str]) -> None:
    _section(pdf, "Approvals & Signatures")
    pdf.set_font(TEXT, "", 9.5)
    for line in lines:
        pdf.cell(0, 7, f"  [SIGNED]  {line}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def learning_agreement_pdf(student: str, host: str, start: str, end: str, doc_id: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _letterhead(pdf, "Learning Agreement for Studies", doc_id)

    _section(pdf, "Student Details")
    _kv_table(
        pdf,
        [
            ("Student", student),
            ("Email", f"{student.split()[0].lower()}@student.example.edu"),
            ("Sending institution", "Erasmus Home University"),
            ("Receiving institution", host),
        ],
    )

    _section(pdf, "Table A - Educational Components at the Host Institution")
    with pdf.table(col_widths=(25, 65, 20, 20)) as table:
        row = table.row()
        for h in ["Code", "Course title", "Semester", "ECTS"]:
            row.cell(h)
        for code, title, ects in [
            ("INFO-401", "Advanced Web Architectures", "6"),
            ("INFO-405", "Cloud & Distributed Systems", "6"),
        ]:
            row = table.row()
            for v in [code, title, "1st", ects]:
                row.cell(v)
    pdf.ln(4)

    _section(pdf, "Table B - Recognition at the Home Institution")
    with pdf.table(col_widths=(25, 65, 20)) as table:
        row = table.row()
        for h in ["Code", "Equivalent course", "ECTS recognised"]:
            row.cell(h)
        row = table.row()
        for v in ["309102", "Web and Cloud Architectures", "12"]:
            row.cell(v)
    pdf.ln(4)

    _signature_block(
        pdf,
        [
            "Student",
            "Sending institution coordinator",
            "Receiving institution coordinator",
        ],
    )
    return bytes(pdf.output())


def certificate_pdf(student: str, host: str, start: str, end: str, doc_id: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _letterhead(pdf, "Certificate of Arrival & Departure", doc_id)

    _section(pdf, "Student Information")
    _kv_table(pdf, [("Student", student), ("Host university", host)])

    _section(pdf, "Part 1 - Certificate of Arrival")
    _kv_table(
        pdf,
        [
            ("Arrival date", start),
            ("International office representative", "Jean Dupont"),
            ("Signed and stamped", "Yes"),
        ],
    )

    _section(pdf, "Part 2 - Certificate of Departure")
    _kv_table(
        pdf,
        [
            ("Departure date", end),
            ("Signed and stamped", "Yes"),
        ],
    )

    _signature_block(pdf, ["International Relations Office"])
    return bytes(pdf.output())


def insurance_pdf(student: str, host: str, start: str, end: str, doc_id: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _letterhead(pdf, "Insurance Confirmation Document", doc_id)

    _section(pdf, "Policy Header")
    _kv_table(
        pdf,
        [
            ("Insured student", student),
            ("Policy number", f"EUR-2026-{abs(hash(student)) % 9999:04d}"),
            ("Provider", "Erasmus Protect Global Insurance"),
            ("Territorial validity", "European Union + associated countries"),
        ],
    )

    _section(pdf, "Coverage Detail")
    with pdf.table(col_widths=(55, 35, 25)) as table:
        row = table.row()
        for h in ["Coverage type", "Limit", "Status"]:
            row.cell(h)
        for ctype, limit in [
            ("Health & Accident", "EUR 50,000"),
            ("Personal Liability (RC)", "EUR 500,000"),
            ("Travel Assistance & Repatriation", "Full cost"),
        ]:
            row = table.row()
            for v in [ctype, limit, "Active"]:
                row.cell(v)
    pdf.ln(4)

    _section(pdf, "Validity")
    _kv_table(pdf, [("Coverage period", f"{start} to {end}")])
    return bytes(pdf.output())


def transcript_pdf(student: str, host: str, start: str, end: str, doc_id: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _letterhead(pdf, "Transcript of Records", doc_id)

    _section(pdf, "Host Institution")
    _kv_table(pdf, [("Institution", host), ("Country", "-"), ("Erasmus code", "-")])

    _section(pdf, "Student")
    _kv_table(pdf, [("Student", student), ("Host student ID", f"ID-{abs(hash(student)) % 9999:04d}")])

    _section(pdf, "Examinations")
    with pdf.table(col_widths=(22, 48, 25, 15, 20, 15)) as table:
        row = table.row()
        for h in ["Code", "Course title", "Exam date", "ECTS", "Local grade", "ECTS grade"]:
            row.cell(h)
        for code, title, date, ects, local, grade in [
            ("INFO-401", "Advanced Web Architectures", "2027-01-20", "6", "18/20", "A"),
            ("INFO-405", "Cloud & Distributed Systems", "2027-02-12", "6", "16/20", "B"),
        ]:
            row = table.row()
            for v in [code, title, date, ects, local, grade]:
                row.cell(v)
    pdf.ln(4)

    _section(pdf, "Summary")
    _kv_table(pdf, [("Total ECTS completed", "12"), ("Weighted average (local)", "17.0 / 20")])

    _signature_block(pdf, ["Head of Academic Affairs"])
    return bytes(pdf.output())


DOC_LAYOUTS = {
    "Learning Agreement": learning_agreement_pdf,
    "Certificate of Arrival": certificate_pdf,
    "Insurance Certificate": insurance_pdf,
    "Transcript of Records": transcript_pdf,
}


def layout_pdf(doc_type: str, student: str, host: str, start: str, end: str, doc_id: str) -> bytes | None:
    """Return the specced layout for a known type, or None to fall back to the plain form."""
    layout = DOC_LAYOUTS.get(doc_type)
    return layout(student, host, start, end, doc_id) if layout else None


# -- "clean" students: everything should classify correctly ---------------
STUDENTS = [
    {
        "first": "Ana",
        "surname": "Garcia Lopez",
        "host": "University of Bologna",
        "start": "2026-09-01",
        "end": "2027-02-28",
        "docs": [("Learning Agreement", "LA_Ana_Garcia.pdf")],
        "subject": "My Learning Agreement",
        "body": "Hello, attached is my signed Learning Agreement for the first semester. Ana",
    },
    {
        "first": "Jonas",
        "surname": "Weber",
        "host": "TU Berlin",
        "start": "2026-10-01",
        "end": "2027-03-31",
        "docs": [("Transcript of Records", "scan_0042.pdf")],
        "subject": "transcript",
        "body": "Hi, here is my transcript. Sorry for the file name. Jonas",
    },
    {
        "first": "Maria",
        "surname": "Rossi",
        "host": "University of Padova",
        "start": "2026-09-15",
        "end": "2027-02-15",
        "docs": [("Insurance Certificate", "IMG_2231.jpg")],
        "subject": "insurance!!!",
        "body": "Good morning, I send the insurance certificate as a photo. Maria",
    },
    {
        "first": "Lucas",
        "surname": "Martin",
        "host": "Universite de Lyon",
        "start": "2026-09-05",
        "end": "2027-01-30",
        "docs": [("Certificate of Arrival", "IMG_8812.jpg")],
        "subject": "certificate",
        "body": "Hello, my certificate of arrival, signed by the host office. Lucas",
    },
    {
        "first": "Sofia",
        "surname": "Almeida",
        "host": "University of Coimbra",
        "start": "2026-09-10",
        "end": "2027-02-10",
        "docs": [
            ("Learning Agreement", "documento_final_final.pdf"),
            ("Insurance Certificate", "seguro.pdf"),
        ],
        "subject": "documents",
        "body": "Good morning, I am sending the Learning Agreement and the insurance. Thank you, Sofia",
    },
    {
        "first": "Emma",
        "surname": "Dubois",
        "host": "Sorbonne University",
        "start": "2026-09-20",
        "end": "2027-03-20",
        "docs": [("Transcript of Records", "IMG_0007_2.jpg")],
        "subject": "docs",
        "body": "Hello, here is my transcript of records. Emma",
    },
    {
        "first": "Pablo",
        "surname": "Sanchez",
        "host": "University of Valencia",
        "start": "2026-09-01",
        "end": "2027-02-28",
        "docs": [("Learning Agreement", "foto_borrosa.jpg")],
        "subject": "learning agreement",
        "body": "Hi, attached is a photo of the learning agreement, it looks a bit bad. Pablo",
        "blur": True,
    },
    {
        "first": "Lena",
        "surname": "Novak",
        "host": "University of Ljubljana",
        "start": "2026-10-01",
        "end": "2027-02-01",
        "docs": [("Hostel booking confirmation", "dokument_ohne_titel.pdf")],
        "subject": "my document",
        "body": "Hello, please find my document attached. Lena",
    },
    {
        "first": "Tomas",
        "surname": "Ferreira",
        "host": "University of Porto",
        "start": "2026-09-10",
        "end": "2027-02-10",
        "docs": [],
        "subject": "Question about deadline",
        "body": "Hello, when is the deadline to submit the Learning Agreement? Thanks, Tomas",
    },
    {
        "first": "Chiara",
        "surname": "Bianchi",
        "host": "University of Milan",
        "start": "2026-09-12",
        "end": "2027-02-12",
        "docs": [("Certificate of Arrival", "certificato_arrivo.pdf")],
        "subject": "certificate of arrival",
        "body": "Dear office, please find my certificate of arrival. Chiara",
    },
    # -- deliberately broken cases, each a different failure mode ---------
    {
        "first": "Noor",
        "surname": "",
        "host": "University of Amsterdam",
        "start": "2026-09-01",
        "end": "2027-02-01",
        "subject": "my document",
        "body": "Hi, here is my learning agreement. Thanks",
        "attachments": [
            {
                "filename": "la_noor.pdf",
                "kind": "form",
                "lines": [
                    "Document: Learning Agreement",
                    "Student: Noor",
                    "Host university: University of Amsterdam",
                    "Stay start: 2026-09-01",
                    "Stay end: 2027-02-01",
                    "Deadline: 2026-10-15",
                    "Academic year: 2026-27",
                    "Signature illegible, surname not readable on the scan.",
                ],
            }
        ],
    },
    {
        "first": "Erik",
        "surname": "Johansson",
        "host": "Uppsala University",
        "start": "2026-09-01",
        "end": "2027-02-01",
        "docs": [("Transcript of Records", "mixed_up.pdf")],
        "subject": "insurance",
        "body": "Hi, here is my insurance as requested. Erik",
    },
    {
        "first": "Yuki",
        "surname": "Tanaka",
        "host": "Politecnico di Torino",
        "start": "2026-09-01",
        "end": "2027-02-01",
        "subject": "Learning Agreement attached",
        "body": "Hello, please find attached my Learning Agreement in Word format.",
        "attachments": [
            {
                "filename": "learning_agreement.docx",
                "kind": "raw",
                "mime": ("application", "vnd.openxmlformats-officedocument.wordprocessingml.document"),
                "raw_bytes": b"PK\x03\x04 (not a real docx, just bytes for the demo)",
            }
        ],
    },
    {
        "first": "Priya",
        "surname": "Nair",
        "host": "KU Leuven",
        "start": "2026-09-01",
        "end": "2027-02-01",
        "subject": "transcript",
        "body": "Hi, here is my transcript, let me know if you can't open it.",
        "attachments": [
            {
                "filename": "transcript_broken.pdf",
                "kind": "raw",
                "mime": ("application", "pdf"),
                "raw_bytes": b"%PDF-1.4 THIS FILE IS INTENTIONALLY CORRUPTED AND NOT A REAL PDF",
            }
        ],
    },
    {
        "first": "Oliver",
        "surname": "Smith",
        "host": "Trinity College Dublin",
        "start": "2026-09-01",
        "end": "2027-02-01",
        "subject": "look at this",
        "body": "Hey just wanted to share a pic from my trip :)",
        "attachments": [
            {
                "filename": "IMG_9981.jpg",
                "kind": "image_random",
                "lines": ["Exchange trip day 1!", "Best semester ever 🎉", "(not an official document)"],
            }
        ],
    },
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def build_email(entry: dict) -> EmailMessage:
    message = EmailMessage()
    display_name = f"{entry['first']} {entry['surname']}".strip()
    message["From"] = f"{display_name} <student@example.com>"
    message["To"] = "erasmus@example.edu"
    message["Subject"] = entry["subject"]
    message.set_content(entry["body"])

    student = f"{entry['first']} {entry['surname']}".strip()

    for att in entry.get("attachments", []):
        kind = att.get("kind", "form")
        filename = att["filename"]
        if kind == "raw":
            payload = att["raw_bytes"]
            maintype, subtype = att["mime"]
        elif kind == "image_random":
            payload = make_image(att["lines"], blur=att.get("blur", False), official=False)
            maintype, subtype = "image", "jpeg"
        else:
            lines = att.get("lines")
            extension = Path(filename).suffix.lower()
            if extension in IMAGE_EXTENSIONS:
                payload = make_image(lines or [], blur=att.get("blur", False))
                maintype, subtype = "image", "jpeg"
            else:
                payload = make_pdf(lines or [])
                maintype, subtype = "application", "pdf"
        message.add_attachment(payload, maintype=maintype, subtype=subtype, filename=filename)

    for doc_index, (doc_type, filename) in enumerate(entry.get("docs", []), start=1):
        extension = Path(filename).suffix.lower()
        if extension in IMAGE_EXTENSIONS:
            lines = document(doc_type, student, entry["host"], entry["start"], entry["end"])
            payload = make_image(lines, blur=entry.get("blur", False))
            maintype, subtype = "image", "jpeg"
        else:
            doc_id = f"{entry['first'][:2].upper()}{entry['surname'][:2].upper()}-{doc_index:02d}"
            specced = layout_pdf(doc_type, student, entry["host"], entry["start"], entry["end"], doc_id)
            if specced is not None:
                payload = specced
            else:
                lines = document(doc_type, student, entry["host"], entry["start"], entry["end"])
                payload = make_pdf(lines)
            maintype, subtype = "application", "pdf"
        message.add_attachment(payload, maintype=maintype, subtype=subtype, filename=filename)

    return message


def main() -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    random.seed(7)
    for index, entry in enumerate(STUDENTS, start=1):
        message = build_email(entry)
        target = INBOX / f"email_{index:02d}.eml"
        target.write_bytes(bytes(message))
        n_docs = len(entry.get("docs", [])) + len(entry.get("attachments", []))
        print(f"wrote {target.name}: {entry['first']} {entry['surname']} ({n_docs} attachments)")

    expected = ROOT / "data" / "expected.csv"
    with expected.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["email", "first", "surname", "doc_type", "semester", "host", "start", "end"])
        for index, entry in enumerate(STUDENTS, start=1):
            for doc_type, _ in entry.get("docs", []):
                writer.writerow(
                    [
                        f"email_{index:02d}.eml",
                        entry["first"],
                        entry["surname"],
                        doc_type,
                        "2026-27",
                        entry["host"],
                        entry["start"],
                        entry["end"],
                    ]
                )
    print(f"wrote {expected.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
