"""Local PDF export for vacancy-specific cover letters."""

from __future__ import annotations

import os
import re
import tempfile
from html import escape
from pathlib import Path

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


class CoverLetterPdfError(ValueError):
    """Raised when a cover letter cannot be exported safely."""


def suggested_cover_letter_filename(company: str, title: str) -> str:
    raw = f"Anschreiben_{company}_{title}"
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", raw)
    cleaned = re.sub(r"\s+", "_", cleaned).strip(" ._")
    return f"{cleaned[:120] or 'Anschreiben'}.pdf"


def _font_name() -> str:
    candidates = (
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeui.ttf",
    )
    for path in candidates:
        if path.is_file():
            name = "JobCompassSans"
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(path)))
            return name
    return "Helvetica"


def export_cover_letter_pdf(text: str, destination: str | Path) -> Path:
    """Write an A4 PDF atomically and return its absolute path."""
    content = text.strip()
    if not content:
        raise CoverLetterPdfError("Супровідний лист порожній.")
    output = Path(destination).expanduser().resolve()
    if output.suffix.casefold() != ".pdf":
        output = output.with_suffix(".pdf")
    output.parent.mkdir(parents=True, exist_ok=True)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.stem}-",
            suffix=".pdf",
            dir=output.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        styles = getSampleStyleSheet()
        body = ParagraphStyle(
            "JobCompassCoverLetter",
            parent=styles["BodyText"],
            fontName=_font_name(),
            fontSize=11,
            leading=16,
            alignment=TA_LEFT,
            spaceAfter=4 * mm,
        )
        story = []
        for block in re.split(r"\n\s*\n", content):
            rendered = "<br/>".join(escape(line) for line in block.splitlines())
            if rendered:
                story.extend((Paragraph(rendered, body), Spacer(1, 1.5 * mm)))
        document = SimpleDocTemplate(
            str(temporary_path),
            pagesize=A4,
            leftMargin=25 * mm,
            rightMargin=25 * mm,
            topMargin=22 * mm,
            bottomMargin=22 * mm,
            title="Anschreiben",
            author="JobCompass",
        )
        document.build(story)
        temporary_path.replace(output)
    except (OSError, ValueError) as error:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise CoverLetterPdfError(
            f"Не вдалося створити PDF супровідного листа: {error}"
        ) from error
    return output
