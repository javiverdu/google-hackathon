"""Shared data contract. Freeze this before parallel work starts."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class DocType(StrEnum):
    learning_agreement = "LearningAgreement"
    transcript = "Transcript"
    insurance = "Insurance"
    certificate_of_arrival = "CertificateOfArrival"
    other = "Other"


REQUIRED_DOCS: tuple[DocType, ...] = (
    DocType.learning_agreement,
    DocType.transcript,
    DocType.insurance,
    DocType.certificate_of_arrival,
)


class DocumentInfo(BaseModel):
    """Structured output the LLM must return for every attachment."""

    student_first_name: str = Field(default="", description="Student first name")
    student_surname: str = Field(default="", description="Student surname")
    doc_type: DocType = Field(default=DocType.other, description="Document type")
    semester: str = Field(default="", description="Academic year, e.g. 2026-27")
    host_university: str = Field(default="", description="Host university")
    start_date: str = Field(default="", description="Stay start, ISO YYYY-MM-DD")
    end_date: str = Field(default="", description="Stay end, ISO YYYY-MM-DD")
    deadline: str = Field(default="", description="Relevant deadline, ISO YYYY-MM-DD")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: str = Field(default="", description="Short reason for low confidence")


def slug(value: str) -> str:
    """ASCII-safe, filename-safe token: 'Núñez' -> 'Nunez', 'Garcia Lopez' -> 'GarciaLopez'."""
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    words = [word for word in re.split(r"[^A-Za-z0-9]+", value) if word]
    return "".join(word[:1].upper() + word[1:] for word in words) or "Unknown"


def semester_tag(value: str) -> str:
    """Normalise '2026/2027', '2026-2027', '26-27' to '2026-27'."""
    years = re.findall(r"\d{2,4}", value or "")
    if len(years) >= 2:
        first, second = years[0], years[1]
        if len(first) == 2:
            first = "20" + first
        if len(second) == 2:
            second = first[:2] + second
        return f"{first}-{second[2:]}"
    return value.strip().replace("/", "-") or "unknown"


def build_filename(info: DocumentInfo, suffix: str = ".pdf") -> str:
    """Surname_Name_DocType_2026-27.pdf"""
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return "_".join(
        [
            slug(info.student_surname),
            slug(info.student_first_name),
            info.doc_type.value,
            semester_tag(info.semester),
        ]
    ) + suffix.lower()


def file_suffix(name: str, default: str = ".pdf") -> str:
    return Path(name).suffix or default


def parse_date(value: str) -> date | None:
    """Accept only strict ISO dates; LLM output can contain anything."""
    try:
        return date.fromisoformat((value or "").strip()[:10])
    except ValueError:
        return None


def is_expired(end_date: str, today: date | None = None) -> bool:
    """True only for a valid date strictly before today."""
    parsed = parse_date(end_date)
    if parsed is None:
        return False
    return parsed < (today or date.today())
