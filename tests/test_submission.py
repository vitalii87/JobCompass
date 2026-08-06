from __future__ import annotations

import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from app.core.models import CandidateProfile, SubmissionMode
from app.services.submission import (
    SubmissionPreparationError,
    prepare_submission,
    resume_sha256,
)


class SubmissionPreparationTests(unittest.TestCase):
    def test_original_resume_is_hashed_and_snapshotted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            resume = Path(directory) / "Lebenslauf.pdf"
            content = b"original pdf bytes"
            resume.write_bytes(content)

            submission = prepare_submission(
                mode=SubmissionMode.ASSISTED,
                destination_url="https://example.test/job",
                resume_path=str(resume),
                cover_letter_text="Anschreiben",
                profile=CandidateProfile(
                    full_name="Anna", email="anna@example.test", phone="123"
                ),
            )

            self.assertEqual(submission.resume_name, "Lebenslauf.pdf")
            self.assertEqual(submission.resume_sha256, sha256(content).hexdigest())
            self.assertEqual(submission.cover_letter_text, "Anschreiben")
            self.assertEqual(submission.contact_full_name, "Anna")

    def test_missing_original_resume_is_rejected(self) -> None:
        with self.assertRaises(SubmissionPreparationError):
            resume_sha256("missing-resume.pdf")

    def test_manual_submission_can_continue_without_resume(self) -> None:
        submission = prepare_submission(
            mode=SubmissionMode.MANUAL,
            destination_url="https://example.test/job",
            profile=CandidateProfile(),
        )

        self.assertEqual(submission.resume_path, "")
        self.assertEqual(submission.resume_sha256, "")


if __name__ == "__main__":
    unittest.main()
