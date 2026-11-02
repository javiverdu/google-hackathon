"""Read the generated sample emails without touching the LLM."""

from pathlib import Path

import pytest

from erasmus_agent.tools.email_reader import iter_inbox, read_email

INBOX = Path(__file__).resolve().parent.parent / "data" / "inbox"
SAMPLE = INBOX / "email_01.eml"


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample data not generated")
def test_read_email():
    meta = read_email(SAMPLE)
    assert meta["subject"]
    assert meta["attachments"]
    assert meta["attachments"][0]["data"][:4] == b"%PDF"


@pytest.mark.skipif(not INBOX.exists(), reason="sample data not generated")
def test_iter_inbox_reads_all():
    emails = list(iter_inbox(INBOX))
    assert len(emails) == 10
    assert all("filename" in meta for meta in emails)
