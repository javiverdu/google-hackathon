"""Web download: filename rules, size limits, scheme checks and pipeline handoff."""

from __future__ import annotations

import pytest

import erasmus_agent.pipeline as pipeline
import erasmus_agent.tools.web_download as web_download
from erasmus_agent.tools.web_download import download_document, filename_from_headers
from tests.helpers import make_info


class FakeHeaders(dict):
    def get_content_type(self):
        return self.get("Content-Type", "application/octet-stream").split(";")[0]


class FakeResponse:
    def __init__(self, data=b"%PDF-1.4 web", headers=None):
        self.data = data
        self.headers = FakeHeaders(headers or {})

    def read(self, size=-1):
        return self.data if size < 0 else self.data[:size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_filename_from_content_disposition():
    name = filename_from_headers(
        'attachment; filename="Learning Agreement.pdf"', "https://x.test/download?id=1"
    )
    assert name == "Learning Agreement.pdf"


def test_filename_falls_back_to_url_path():
    name = filename_from_headers(None, "https://x.test/files/scan_0042.pdf?token=abc")
    assert name == "scan_0042.pdf"


def test_filename_guess_extension_from_mime():
    name = filename_from_headers(None, "https://x.test/download/1234", "application/pdf")
    assert name.endswith(".pdf")


def test_filename_strips_path_traversal():
    name = filename_from_headers('attachment; filename="../../evil.pdf"', "https://x.test/x.pdf")
    assert "/" not in name
    assert "\\" not in name
    assert name.endswith(".pdf")


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://x.test/a.pdf", "not-a-url"])
def test_only_http_urls_allowed(monkeypatch, url):
    with pytest.raises(ValueError, match="Only http"):
        download_document(url)


def test_content_length_over_limit_is_rejected(monkeypatch):
    response = FakeResponse(headers={"Content-Length": "999999"})
    monkeypatch.setattr(web_download, "urlopen", lambda *args, **kwargs: response)

    with pytest.raises(ValueError, match="too large"):
        download_document("https://x.test/big.pdf", max_bytes=10)


def test_body_over_limit_is_rejected(monkeypatch):
    response = FakeResponse(data=b"x" * 50)
    monkeypatch.setattr(web_download, "urlopen", lambda *args, **kwargs: response)

    with pytest.raises(ValueError, match="too large"):
        download_document("https://x.test/big.pdf", max_bytes=10)


def test_successful_download_returns_name_and_bytes(monkeypatch):
    response = FakeResponse(
        data=b"%PDF-1.4 body",
        headers={
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="certificado.pdf"',
        },
    )
    monkeypatch.setattr(web_download, "urlopen", lambda *args, **kwargs: response)

    result = download_document("https://x.test/files/123")
    assert result["name"] == "certificado.pdf"
    assert result["data"] == b"%PDF-1.4 body"
    assert result["content_type"] == "application/pdf"


def test_process_url_uses_normal_naming_and_spreadsheet(env, monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "download_document",
        lambda url: {"name": "scan_0042.pdf", "data": b"%PDF-1.4", "content_type": "application/pdf"},
    )
    monkeypatch.setattr(pipeline.llm, "classify_document", lambda meta, attachment: make_info())

    report = pipeline.process_url("https://x.test/scan")

    assert report["saved"] == ["Garcia_Ana_LearningAgreement_2026-27.pdf"]
    assert (env.out / "Garcia_Ana_LearningAgreement_2026-27.pdf").exists()
