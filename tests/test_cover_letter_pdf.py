from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader

from app.services.cover_letter_pdf import (
    CoverLetterPdfError,
    export_cover_letter_pdf,
    suggested_cover_letter_filename,
)


class CoverLetterPdfTests(unittest.TestCase):
    def test_exports_readable_german_cover_letter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = export_cover_letter_pdf(
                "Sehr geehrte Damen und Herren,\n\n"
                "ich bewerbe mich für die ausgeschriebene Position.\n\n"
                "Mit freundlichen Grüßen",
                Path(directory) / "anschreiben.pdf",
            )

            self.assertTrue(output.read_bytes().startswith(b"%PDF-"))
            extracted = "\n".join(
                page.extract_text() or "" for page in PdfReader(output).pages
            )
            self.assertIn("ausgeschriebene Position", extracted)
            self.assertIn("Grüßen", extracted)

    def test_empty_letter_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(CoverLetterPdfError):
                export_cover_letter_pdf("  ", Path(directory) / "empty.pdf")

    def test_suggested_filename_is_windows_safe(self) -> None:
        self.assertEqual(
            suggested_cover_letter_filename('ACME: GmbH', 'Office/Manager?'),
            "Anschreiben_ACME__GmbH_Office_Manager.pdf",
        )


if __name__ == "__main__":
    unittest.main()
