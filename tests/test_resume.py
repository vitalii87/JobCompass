from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.core.matcher import JobMatcher
from app.core.models import JobPosting
from app.services.resume import load_resume


def _minimal_pdf(lines: tuple[str, ...]) -> bytes:
    commands = ["BT", "/F1 12 Tf", "72 720 Td"]
    for line in lines:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.extend((f"({escaped}) Tj", "0 -20 Td"))
    commands.append("ET")
    content = "\n".join(commands).encode("ascii")
    objects = (
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n"
        + content
        + b"\nendstream",
    )
    document = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{number} 0 obj\n".encode("ascii"))
        document.extend(body)
        document.extend(b"\nendobj\n")
    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(document)


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

    def test_text_pdf_is_read_locally(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resume.pdf"
            path.write_bytes(
                _minimal_pdf(("Skills: Python, SQL", "Languages: German B2"))
            )

            result = load_resume(path)

        self.assertIn("Skills: Python, SQL", result.raw_text)
        self.assertEqual(result.profile.skills, ("Python", "SQL"))
        self.assertEqual(result.profile.languages, ("German B2",))

    def test_image_only_pdf_explains_that_ocr_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scan.pdf"
            path.write_bytes(_minimal_pdf(()))

            with self.assertRaisesRegex(ValueError, "OCR"):
                load_resume(path)

    def test_resume_without_identity_fields_is_still_usable(self) -> None:
        text = """Python und Docker
4 Jahre Berufserfahrung
Deutsch B2
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lebenslauf.txt"
            path.write_text(text, encoding="utf-8")

            result = load_resume(path)

        self.assertEqual(result.profile.full_name, "")
        self.assertEqual(result.profile.email, "")
        self.assertEqual(result.profile.desired_roles, ())
        self.assertEqual(result.profile.skills, ("Python", "Docker"))
        self.assertEqual(result.profile.languages, ("German B2",))
        self.assertEqual(result.profile.years_experience, 4)
        match = JobMatcher().match(
            result.profile,
            JobPosting(
                source="test",
                external_id="resume-only",
                title="Python-Entwickler",
                company="Example GmbH",
                required_skills=("Python", "Docker"),
            ),
        )
        self.assertEqual(match.score, 100)

    def test_german_resume_headings_are_recognized(self) -> None:
        text = """Name: Vitalii
Wunschposition: Softwareentwickler
Kenntnisse: Python, SQL, Git
Sprachen: Deutsch, Englisch
Wohnort: Stuttgart
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lebenslauf.txt"
            path.write_text(text, encoding="utf-8")

            result = load_resume(path)

        self.assertEqual(result.profile.desired_roles, ("Softwareentwickler",))
        self.assertEqual(result.profile.skills, ("Python", "SQL", "Git"))
        self.assertEqual(result.profile.languages, ("Deutsch", "Englisch"))

    def test_german_administrative_skills_are_extracted(self) -> None:
        text = """Wunschposition: Kaufmännische Assistenz
Kenntnisse: MS Office, Excel, SAP, Terminkoordination, Rechnungsprüfung
Sprachen: Deutsch B2
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lebenslauf-verwaltung.txt"
            path.write_text(text, encoding="utf-8")

            result = load_resume(path)

        self.assertEqual(result.profile.desired_roles, ("Kaufmännische Assistenz",))
        self.assertTrue(
            {
                "Microsoft Office",
                "Microsoft Excel",
                "SAP",
                "Calendar Management",
                "Invoice Processing",
            }.issubset(set(result.profile.skills))
        )


if __name__ == "__main__":
    unittest.main()
