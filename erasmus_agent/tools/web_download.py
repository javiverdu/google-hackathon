"""Download a document from a web page and hand it to the normal pipeline.

Only direct links to files are supported. Normal web pages are rejected with a
clear message instead of being fed to the classifier as a fake document.
"""

from __future__ import annotations

import ipaddress
import mimetypes
import re
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from ..config import MAX_ATTACHMENT_BYTES

_UNSAFE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_HTML_TYPES = {"text/html", "application/xhtml+xml"}
_BLOCKED_HOSTS = {"localhost", "localhost.localdomain", "metadata.google.internal"}

HTML_HINT = (
    "That URL is a web page, not a document. Paste a direct link to the file "
    "(for example a URL ending in .pdf, .jpg or .png). Pages that need a login, "
    "a button click or a file picker cannot be downloaded."
)


class DownloadError(ValueError):
    """Download failure with a user-facing message and a category."""

    def __init__(self, message: str, kind: str = "error"):
        super().__init__(message)
        self.kind = kind


def _blocked_host(host: str) -> bool:
    name = (host or "").strip("[]").lower()
    if name in _BLOCKED_HOSTS:
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local or address.is_reserved


def filename_from_headers(disposition: str | None, url: str, content_type: str = "") -> str:
    """Prefer Content-Disposition, then the URL path, then a MIME extension."""
    name = ""
    if disposition:
        message = Message()
        message["Content-Disposition"] = disposition
        name = message.get_filename() or ""
    if not name:
        name = unquote(Path(urlparse(url).path).name)
    name = _UNSAFE.sub("_", name).strip(" .") or "download"
    if not Path(name).suffix:
        name += mimetypes.guess_extension(content_type or "") or ".bin"
    return name[:120]


def _looks_like_html(content_type: str, data: bytes) -> bool:
    if content_type.lower() in _HTML_TYPES:
        return True
    head = data[:512].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def download_document(
    url: str,
    timeout: int = 20,
    max_bytes: int | None = None,
) -> dict:
    """Fetch http(s) only; returns {'name', 'data', 'content_type'}."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise DownloadError(
            "Only http(s) URLs are allowed. A local path or file link cannot be downloaded.",
            kind="scheme",
        )
    if not parsed.netloc or _blocked_host(parsed.hostname or ""):
        raise DownloadError(
            "That address is not reachable from the public app. Use a public link.",
            kind="network",
        )

    limit = max_bytes or MAX_ATTACHMENT_BYTES
    request = Request(url.strip(), headers={"User-Agent": "ErasmusDocFlow/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - scheme checked above
            length = response.headers.get("Content-Length")
            if length and length.isdigit() and int(length) > limit:
                raise DownloadError(
                    f"The file is too large ({int(length) // (1024 * 1024)} MB). "
                    f"Maximum size is {limit // (1024 * 1024)} MB.",
                    kind="too_large",
                )

            data = response.read(limit + 1)
            if len(data) > limit:
                raise DownloadError(
                    f"The file is too large: more than {limit // (1024 * 1024)} MB.",
                    kind="too_large",
                )

            content_type = ""
            if hasattr(response.headers, "get_content_type"):
                content_type = response.headers.get_content_type() or ""
            content_type = content_type or response.headers.get("Content-Type", "").split(";")[0]
            content_type = content_type.strip()
            name = filename_from_headers(
                response.headers.get("Content-Disposition"), url, content_type
            )
    except HTTPError as exc:
        if exc.code == 404:
            raise DownloadError("The link returned 404: the file does not exist.", kind="not_found") from exc
        if exc.code in {401, 403}:
            raise DownloadError(
                "The link needs a login or is private, so it cannot be downloaded.",
                kind="auth",
            ) from exc
        raise DownloadError(f"The server answered with HTTP {exc.code}.", kind="http") from exc
    except URLError as exc:
        raise DownloadError(
            f"Cannot reach that link ({exc.reason}). Check the address.",
            kind="network",
        ) from exc
    except TimeoutError as exc:
        raise DownloadError(
            "The download timed out. Try again or use a smaller file.",
            kind="timeout",
        ) from exc

    if not data:
        raise DownloadError("The link returned an empty file.", kind="empty")
    if _looks_like_html(content_type, data):
        raise DownloadError(HTML_HINT, kind="html")

    return {"name": name, "data": data, "content_type": content_type}
