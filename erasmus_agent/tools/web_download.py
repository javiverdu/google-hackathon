"""Download a document from a web page and hand it to the normal pipeline."""

from __future__ import annotations

import mimetypes
import re
from email.message import Message
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from ..config import MAX_ATTACHMENT_BYTES

_UNSAFE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


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


def download_document(
    url: str,
    timeout: int = 20,
    max_bytes: int | None = None,
) -> dict:
    """Fetch http(s) only; returns {'name', 'data', 'content_type'}."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Only http(s) URLs are allowed, got: {parsed.scheme or 'none'}")

    limit = max_bytes or MAX_ATTACHMENT_BYTES
    request = Request(url, headers={"User-Agent": "ErasmusDocFlow/0.1"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - scheme checked above
        length = response.headers.get("Content-Length")
        if length and int(length) > limit:
            raise ValueError(f"File too large: {length} bytes (max {limit})")
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError(f"File too large: more than {limit} bytes")

        content_type = ""
        if hasattr(response.headers, "get_content_type"):
            content_type = response.headers.get_content_type() or ""
        content_type = content_type or response.headers.get("Content-Type", "").split(";")[0]
        name = filename_from_headers(
            response.headers.get("Content-Disposition"), url, content_type
        )

    return {"name": name, "data": data, "content_type": content_type}
