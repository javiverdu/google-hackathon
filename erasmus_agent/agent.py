"""ADK agent entrypoint. Run locally with: adk web

The hosted Streamlit app calls the same underlying functions in erasmus_agent.pipeline.
"""

from __future__ import annotations

from google.adk.agents import Agent

from .config import GEMINI_MODEL, INBOX_DIR, SPREADSHEET
from .pipeline import process_email, run_inbox
from .schemas import build_filename
from .tools.email_reader import iter_inbox
from .tools.excel_writer import read_students
from .tools.faq import load_faq, search_faq


def list_inbox() -> list[str]:
    """List the .eml files waiting in the inbox folder."""
    return [meta["filename"] for meta in iter_inbox(INBOX_DIR)]


def process_inbox(limit: int = 10) -> dict:
    """Process up to `limit` emails: rename documents, update the spreadsheet."""
    return run_inbox(INBOX_DIR, limit=limit)


def process_one(filename: str) -> dict:
    """Process a single email by file name, e.g. 'email_03.eml'."""
    for meta in iter_inbox(INBOX_DIR):
        if meta["filename"] == filename:
            return process_email(meta)
    return {"error": f"{filename} not found in {INBOX_DIR}"}


def students() -> list[dict]:
    """Return the current spreadsheet rows, one per student."""
    return read_students(SPREADSHEET)


def faq(question: str) -> str:
    """Answer a student question using the Erasmus office FAQ."""
    return search_faq(question) or load_faq()


def naming_pattern(first: str, surname: str, doc_type: str, semester: str = "2026-27") -> str:
    """Show the canonical file name for one document."""
    from .schemas import DocType, DocumentInfo

    try:
        parsed = DocType(doc_type)
    except ValueError:
        parsed = DocType.other
    return build_filename(
        DocumentInfo(
            student_first_name=first,
            student_surname=surname,
            doc_type=parsed,
            semester=semester,
        )
    )


root_agent = Agent(
    name="erasmus_document_agent",
    model=GEMINI_MODEL,
    description="Processes Erasmus student emails, documents and questions.",
    instruction=(
        "You are the Erasmus international office assistant. "
        "Use list_inbox and process_inbox to handle incoming emails, then report "
        "what was saved and what went to review. Use students for the spreadsheet. "
        "Use faq for common questions; if the FAQ does not cover it, say a staff "
        "member will follow up. Never invent dates, deadlines or document status."
    ),
    tools=[list_inbox, process_inbox, process_one, students, faq, naming_pattern],
)
