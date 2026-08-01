from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.services.resume import load_resume


class ResumeLoaderTests(unittest.TestCase):
    def test_labeled_text_is_extracted_conservatively(self) -> None:
        text = """Name: Vitalii
Email: vitalii@example.test
Desired roles: Python Developer, Backend Developer
Skills: Python, SQL, Git
Languages: Ukrainian, English
Experience: 3 years
Location: Berlin
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resume.txt"
            path.write_text(text, encoding="utf-8")

            result = load_resume(path)

        self.assertEqual(result.profile.full_name, "Vitalii")
        self.assertEqual(result.profile.skills, ("Python", "SQL", "Git"))
        self.assertEqual(result.profile.years_experience, 3)
        self.assertTrue(result.warnings)

    def test_json_profile_is_loaded_without_heuristics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resume.json"
            path.write_text(
                json.dumps({"full_name": "Vitalii", "skills": ["Python"]}),
                encoding="utf-8",
            )

            result = load_resume(path)

        self.assertEqual(result.profile.skills, ("Python",))
        self.assertEqual(result.warnings, ())

    def test_docx_text_is_read_with_the_standard_library(self) -> None:
        document_xml = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Name: Vitalii</w:t></w:r></w:p>
    <w:p><w:r><w:t>Skills: Python, SQL</w:t></w:r></w:p>
  </w:body>
</w:document>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resume.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", document_xml)

            result = load_resume(path)

        self.assertEqual(result.profile.full_name, "Vitalii")
        self.assertEqual(result.profile.skills, ("Python", "SQL"))

    def test_pdf_reports_that_a_parser_is_not_available(self) -> None:
        with self.assertRaisesRegex(ValueError, "PDF parsing"):
            load_resume("resume.pdf")


if __name__ == "__main__":
    unittest.main()
