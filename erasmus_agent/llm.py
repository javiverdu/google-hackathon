"""Gemini calls (google-genai). One structured call per attachment."""

from __future__ import annotations

import json
import mimetypes

from google import genai
from google.genai import types

from .config import GEMINI_MODEL, api_key
from .schemas import DocumentInfo

SUPPORTED_MIME = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/heic",
    "image/heif",
}

_PROMPT = """You are the document assistant of a university Erasmus office.
Read the email context and the attached document. Extract the fields.
Rules:
- doc_type must be one of: LearningAgreement, Transcript, Insurance, CertificateOfArrival, Other.
- semester format: 2026-27 (academic year).
- dates as ISO YYYY-MM-DD, empty string if not present. Never invent dates.
- confidence is your own certainty (0-1). Use < 0.7 when the scan is blurry,
  the student is ambiguous, or the document type is unclear.
- notes: one short sentence explaining low confidence, else empty.

Email subject: {subject}
Email sender: {sender}
Email body (truncated):
{body}
"""


def _client() -> genai.Client:
    return genai.Client(api_key=api_key())


def _guess_mime(name: str, declared: str) -> str:
    if declared in SUPPORTED_MIME:
        return declared
    guessed, _ = mimetypes.guess_type(name)
    return guessed or declared


def classify_document(email_meta: dict, attachment: dict) -> DocumentInfo:
    """Send the attachment bytes to Gemini and get fixed fields back."""
    mime = _guess_mime(attachment.get("name", ""), attachment.get("content_type", ""))
    if mime not in SUPPORTED_MIME:
        raise ValueError(f"Unsupported attachment type: {mime}")

    prompt = _PROMPT.format(
        subject=email_meta.get("subject", ""),
        sender=email_meta.get("sender", ""),
        body=(email_meta.get("body", "") or "")[:4000],
    )
    response = _client().models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=attachment["data"], mime_type=mime),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DocumentInfo,
            temperature=0.0,
        ),
    )
    if response.parsed is not None:
        return response.parsed
    return DocumentInfo.model_validate(json.loads(response.text))


def answer_question(question: str, faq_text: str, context: str = "") -> str:
    """Answer only from the FAQ and the student table; otherwise escalate."""
    response = _client().models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_text(
                text=(
                    "You are the Erasmus office assistant. Answer the student question "
                    "using ONLY the FAQ and student data below. If the answer is not "
                    "there, reply exactly: ESCALATE: <one line why a human must answer>. "
                    "Be short and friendly.\n\n"
                    f"FAQ:\n{faq_text}\n\nStudent data:\n{context}\n\nQuestion: {question}"
                )
            )
        ],
        config=types.GenerateContentConfig(temperature=0.2),
    )
    return (response.text or "").strip()


def draft_reply(student_name: str, subject: str, summary: str, faq_text: str) -> str:
    """Nice-to-have: reply draft staff can approve before sending."""
    response = _client().models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_text(
                text=(
                    "Draft a short, friendly email reply from the Erasmus office. "
                    "No invented facts; use the FAQ when relevant. Sign as "
                    "'Erasmus Office'.\n\n"
                    f"Student: {student_name}\nOriginal subject: {subject}\n"
                    f"Context: {summary}\n\nFAQ:\n{faq_text}"
                )
            )
        ],
        config=types.GenerateContentConfig(temperature=0.3),
    )
    return (response.text or "").strip()
