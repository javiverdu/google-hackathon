"""Stamp a signature onto a PDF. Only PDFs can be signed this way -- a photo
attachment has no vector layer to draw on top of, so those stay read-only."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

INK = (24, 48, 110, 255)

POSITIONS = {
    "Bottom-left": "bottom-left",
    "Bottom-center": "bottom-center",
    "Bottom-right": "bottom-right",
}


def render_typed_signature(name: str) -> bytes:
    """Turn a typed name into a slanted, pen-like PNG with a transparent
    background -- no font files needed, so it works the same on every OS."""
    name = (name or "Signature").strip()
    font = ImageFont.load_default(size=54)

    probe = Image.new("RGBA", (10, 10))
    bbox = ImageDraw.Draw(probe).textbbox((0, 0), name, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    pad = 16
    flat = Image.new("RGBA", (text_w + pad * 2, text_h + pad * 2), (255, 255, 255, 0))
    draw = ImageDraw.Draw(flat)
    draw.text((pad - bbox[0], pad - bbox[1]), name, font=font, fill=INK)
    draw.line(
        [(pad, flat.height - 8), (flat.width - pad, flat.height - 8)],
        fill=INK,
        width=2,
    )

    # Shear the flat text to fake a handwritten slant.
    shear = 0.22
    width, height = flat.size
    sheared = flat.transform(
        (width + int(shear * height), height),
        Image.AFFINE,
        (1, shear, 0, 0, 1, 0),
        resample=Image.BICUBIC,
    )

    buffer = BytesIO()
    sheared.save(buffer, format="PNG")
    return buffer.getvalue()


def stamp_signature_on_pdf(
    pdf_bytes: bytes,
    signature_png: bytes,
    position: str = "bottom-right",
    page_index: int = -1,
    width_pt: float = 140.0,
) -> bytes:
    """Overlay the signature image on one page and return a new signed PDF."""
    reader = PdfReader(BytesIO(pdf_bytes))
    index = page_index if page_index >= 0 else len(reader.pages) - 1
    page = reader.pages[index]
    page_w = float(page.mediabox.width)
    page_h = float(page.mediabox.height)

    sig_reader = ImageReader(BytesIO(signature_png))
    img_w, img_h = sig_reader.getSize()
    draw_w = width_pt
    draw_h = draw_w * (img_h / img_w)

    margin = 36.0
    x_positions = {
        "bottom-left": margin,
        "bottom-center": (page_w - draw_w) / 2,
        "bottom-right": page_w - draw_w - margin,
    }
    x = x_positions.get(position, x_positions["bottom-right"])
    y = margin

    overlay_buffer = BytesIO()
    c = canvas.Canvas(overlay_buffer, pagesize=(page_w, page_h))
    c.drawImage(sig_reader, x, y, width=draw_w, height=draw_h, mask="auto")
    c.save()
    overlay_buffer.seek(0)

    overlay_page = PdfReader(overlay_buffer).pages[0]
    page.merge_page(overlay_page)

    writer = PdfWriter()
    for existing_page in reader.pages:
        writer.add_page(existing_page)

    out_buffer = BytesIO()
    writer.write(out_buffer)
    return out_buffer.getvalue()
