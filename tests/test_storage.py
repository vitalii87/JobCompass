from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.core.models import (
    ApplicationStatus,
    ApplicationSubmission,
    CandidateProfile,
    CoverLetterPreparation,
    JobPosting,
    SubmissionMode,
)
from app.storage import LocalJsonStore


class LocalJsonStoreTests(unittest.TestCase):
    def test_global_interface_language_survives_reload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            store = LocalJsonStore(path)
            store.initialize()

            store.save_app_language("en")

            self.assertEqual(LocalJsonStore(path).load_app_language(), "en")

    def test_jobs_and_application_status_survive_reload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            store = LocalJsonStore(path)
            store.create_profile("Vitalii")
            job = JobPosting(
                source="test",
                external_id="1",
                title="Python Developer",
                company="ACME",
            )

            self.assertEqual(store.save_jobs([job]), 1)
            record = store.set_application_status(
                job.job_id, ApplicationStatus.INTERESTING, "Review tomorrow"
            )
            reloaded = LocalJsonStore(path)

            self.assertEqual(reloaded.list_jobs(), [job])
            self.assertEqual(record.status, ApplicationStatus.INTERESTING)
            self.assertEqual(reloaded.list_applications()[0].notes, "Review tomorrow")
            self.assertEqual(len(reloaded.list_applications()[0].history), 1)

    def test_profile_and_full_status_history_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LocalJsonStore(Path(directory) / "jobcompass.json")
            profile = CandidateProfile(
                full_name="Vitalii", skills=("Python",), email="v@example.test"
            )
            job = JobPosting(
                source="test", external_id="2", title="Developer", company="ACME"
            )
            store.save_profile(profile)
            store.save_jobs([job])
            store.set_application_status(job.job_id, ApplicationStatus.APPLIED)
            store.set_application_status(job.job_id, ApplicationStatus.INTERVIEW)

            application = store.get_application(job.job_id)

            self.assertEqual(store.load_profile(), profile)
            self.assertIsNotNone(application)
            assert application is not None
            self.assertEqual(
                [event.status for event in application.history],
                [ApplicationStatus.APPLIED, ApplicationStatus.INTERVIEW],
            )
            self.assertTrue(application.has_submission_history)

    def test_unknown_job_cannot_receive_an_application_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = LocalJsonStore(Path(directory) / "jobcompass.json")

            with self.assertRaises(ValueError):
                store.set_application_status("missing:1", ApplicationStatus.APPLIED)

    def test_cover_letter_material_is_saved_per_vacancy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            store = LocalJsonStore(path)
            store.create_profile("Vitalii")
            job = JobPosting(
                source="test", external_id="letter", title="PMO", company="ACME"
            )
            store.save_jobs([job])
            preparation = CoverLetterPreparation(
                job_id=job.job_id,
                draft="Editable draft",
                prompt="Grounded prompt",
                evidence_summary="Confirmed facts",
                language="de",
                tone="warm",
                length="standard",
                focus="Relocation confirmed",
            )

            store.save_cover_letter_preparation(preparation)
            reloaded = LocalJsonStore(path).get_cover_letter_preparation(job.job_id)

            self.assertEqual(reloaded, preparation)

    def test_confirmed_submission_records_materials_and_blocks_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobcompass.json"
            store = LocalJsonStore(path)
            store.create_profile("Vitalii")
            job = JobPosting(
                source="test", external_id="submit", title="PMO", company="ACME"
            )
            store.save_jobs([job])
            submission = ApplicationSubmission(
                mode=SubmissionMode.ASSISTED,
                destination_url="https://example.test/job",
                resume_name="resume.pdf",
                resume_sha256="b" * 64,
                cover_letter_text="Letter",
            )

            record = store.record_application_submission(job.job_id, submission)

            self.assertEqual(record.status, ApplicationStatus.APPLIED)
            self.assertEqual(record.submissions, (submission,))
            with self.assertRaises(ValueError):
                store.record_application_submission(job.job_id, submission)
            duplicate = store.record_application_submission(
                job.job_id, submission, allow_duplicate=True
            )
            self.assertEqual(len(duplicate.submissions), 2)


if __name__ == "__main__":
    unittest.main()
