"""Web download: filename rules, size limits, scheme checks and pipeline handoff."""

from __future__ import annotations

from urllib.error import HTTPError, URLError

import pytest

import erasmus_agent.pipeline as pipeline
import erasmus_agent.tools.web_download as web_download
from erasmus_agent.tools.web_download import (
    DownloadError,
    download_document,
    filename_from_headers,
)
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


def test_html_page_is_rejected_with_hint(monkeypatch):
    response = FakeResponse(
        data=b"<!DOCTYPE html><html><body>Login required</body></html>",
        headers={"Content-Type": "text/html; charset=utf-8"},
    )
    monkeypatch.setattr(web_download, "urlopen", lambda *args, **kwargs: response)

    with pytest.raises(DownloadError) as info:
        download_document("https://x.test/portal/login")

    assert info.value.kind == "html"
    assert "web page, not a document" in str(info.value)
    assert "direct link" in str(info.value)


def test_html_sniffed_from_body_without_content_type(monkeypatch):
    response = FakeResponse(data=b"<html><head><title>Moodle</title></head></html>")
    monkeypatch.setattr(web_download, "urlopen", lambda *args, **kwargs: response)

    with pytest.raises(DownloadError, match="web page"):
        download_document("https://x.test/course/view.php?id=42")


def test_pdf_with_text_content_type_is_accepted(monkeypatch):
    response = FakeResponse(
        data=b"%PDF-1.4 binary",
        headers={"Content-Type": "text/plain", "Content-Disposition": 'attachment; filename="a.pdf"'},
    )
    monkeypatch.setattr(web_download, "urlopen", lambda *args, **kwargs: response)

    assert download_document("https://x.test/a.pdf")["name"] == "a.pdf"


def test_empty_file_is_reported(monkeypatch):
    response = FakeResponse(data=b"", headers={"Content-Type": "application/pdf"})
    monkeypatch.setattr(web_download, "urlopen", lambda *args, **kwargs: response)

    with pytest.raises(DownloadError, match="empty file") as info:
        download_document("https://x.test/empty.pdf")
    assert info.value.kind == "empty"


def test_404_has_friendly_message(monkeypatch):
    def raise_404(*args, **kwargs):
        raise HTTPError("https://x.test/missing.pdf", 404, "Not Found", {}, None)

    monkeypatch.setattr(web_download, "urlopen", raise_404)

    with pytest.raises(DownloadError, match="404") as info:
        download_document("https://x.test/missing.pdf")
    assert info.value.kind == "not_found"


def test_login_required_page_has_friendly_message(monkeypatch):
    def raise_403(*args, **kwargs):
        raise HTTPError("https://x.test/private.pdf", 403, "Forbidden", {}, None)

    monkeypatch.setattr(web_download, "urlopen", raise_403)

    with pytest.raises(DownloadError, match="login or is private") as info:
        download_document("https://x.test/private.pdf")
    assert info.value.kind == "auth"


def test_unreachable_host_has_friendly_message(monkeypatch):
    def raise_urlerror(*args, **kwargs):
        raise URLError("name or service not known")

    monkeypatch.setattr(web_download, "urlopen", raise_urlerror)

    with pytest.raises(DownloadError, match="Cannot reach") as info:
        download_document("https://does-not-exist.test/a.pdf")
    assert info.value.kind == "network"


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/a.pdf",
        "http://127.0.0.1/a.pdf",
        "http://10.0.0.5/a.pdf",
        "http://192.168.1.10/a.pdf",
        "http://169.254.169.254/latest/meta-data",
    ],
)
def test_private_and_local_addresses_are_blocked(url):
    with pytest.raises(DownloadError, match="not reachable") as info:
        download_document(url)
    assert info.value.kind == "network"

