"""Generate 10 fake Erasmus emails with PDF/JPG attachments.

Usage:
    pip install -r requirements-dev.txt
    python scripts/make_sample_data.py

Writes into data/inbox/ (overwrites files with the same names) and creates
data/expected.csv with the ground truth for quick accuracy checks.
"""

from __future__ import annotations

import csv
import io
import random
from email.message import EmailMessage
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "data" / "inbox"

TEXT = "Helvetica"


def make_pdf(lines: list[str]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font(TEXT, size=12)
    for line in lines:
        pdf.multi_cell(pdf.epw, 8, line)
    return bytes(pdf.output())


def make_image(lines: list[str], blur: bool = False) -> bytes:
    image = Image.new("RGB", (900, 1200), "white")
    draw = ImageDraw.Draw(image)
    y = 70
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
        "ERASMUS+ PROGRAMME",
        f"Document: {doc_type}",
        f"Student: {student}",
        f"Host university: {host}",
        f"Stay start: {start}",
        f"Stay end: {end}",
        f"Deadline: {deadline}",
        "Academic year: 2026-27",
        "Signed and stamped by the host university.",
    ]


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
        "subject": "documentos",
        "body": "Bom dia, envio o Learning Agreement e o seguro. Obrigada, Sofia",
    },
    {
        "first": "Emma",
        "surname": "Dubois",
        "host": "Sorbonne University",
        "start": "2026-09-20",
        "end": "2027-03-20",
        "docs": [("Transcript of Records", "IMG_0007_2.jpg")],
        "subject": "docs",
        "body": "Bonjour, voici mon releve de notes. Emma",
    },
    {
        "first": "Pablo",
        "surname": "Sanchez",
        "host": "University of Valencia",
        "start": "2026-09-01",
        "end": "2027-02-28",
        "docs": [("Learning Agreement", "foto_borrosa.jpg")],
        "subject": "learning agreement",
        "body": "Hola, adjunto foto del learning agreement, se ve un poco mal. Pablo",
        "blur": True,
    },
    {
        "first": "Lena",
        "surname": "Novak",
        "host": "University of Ljubljana",
        "start": "2026-10-01",
        "end": "2027-02-01",
        "docs": [("Hostel booking confirmation", "dokument_ohne_titel.pdf")],
        "subject": "mein Dokument",
        "body": "Hallo, anbei mein Dokument. Lena",
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
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def build_email(entry: dict) -> EmailMessage:
    message = EmailMessage()
    message["From"] = f"{entry['first']} {entry['surname']} <student@example.com>"
    message["To"] = "erasmus@example.edu"
    message["Subject"] = entry["subject"]
    message.set_content(entry["body"])

    for doc_type, filename in entry["docs"]:
        student = f"{entry['first']} {entry['surname']}"
        lines = document(doc_type, student, entry["host"], entry["start"], entry["end"])
        extension = Path(filename).suffix.lower()
        if extension in IMAGE_EXTENSIONS:
            payload = make_image(lines, blur=entry.get("blur", False))
            maintype, subtype = "image", "jpeg"
        else:
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
        print(f"wrote {target.name}: {entry['first']} {entry['surname']} ({len(entry['docs'])} attachments)")

    expected = ROOT / "data" / "expected.csv"
    with expected.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["email", "first", "surname", "doc_type", "semester", "host", "start", "end"])
        for index, entry in enumerate(STUDENTS, start=1):
            for doc_type, _ in entry["docs"]:
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
